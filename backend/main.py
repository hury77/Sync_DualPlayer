from fastapi import FastAPI, UploadFile, File, Form, HTTPException, BackgroundTasks, Request
from config import settings
from fastapi.responses import JSONResponse, StreamingResponse, FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import os
import uuid
import subprocess
import asyncio
import re
import time
import shutil
import asyncio
from pathlib import Path
import imageio_ffmpeg
import cv2
import numpy as np
import base64
import threading
from models import (
    FileUploadResponse, FileMetadata, FileStatusResponse, DeleteFileResponse,
    UploadBriefResponse, ClearAssetsResponse, DebugAssetsResponse,
    CopydeckParseResponse, AnalyzeFrameRequest
)
import state
import video_service
import brief_service
from copydeck_service import process_copydeck_file

app = FastAPI(title="Sync DualPlayer API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)




@app.post("/api/v1/files/upload", response_model=FileUploadResponse)
async def upload_file(background_tasks: BackgroundTasks, file: UploadFile = File(...), file_type: str = Form(...)):
    ext = Path(file.filename).suffix.lower()
    if ext not in [".mp4", ".mov", ".mxf", ".gif"]:
        raise HTTPException(status_code=422, detail=f"Niedozwolony format pliku: {ext}. Dozwolone: .mp4, .mov, .mxf, .gif")
        
    return await video_service.process_video_upload(background_tasks, file)

@app.get("/api/v1/files/{file_id}", response_model=FileStatusResponse)
async def get_file_status(file_id: int):
    return video_service.get_status(file_id)

@app.get("/api/v1/files/stream/{file_id}", response_class=FileResponse)
async def stream_file(request: Request, file_id: int):
    return video_service.get_file_stream(file_id)

@app.delete("/api/v1/files/{file_id}", response_model=DeleteFileResponse)
async def delete_file(file_id: int):
    return video_service.delete_file(file_id)


from parsers import parse_filename, ParserError


def match_template(image_np, template_path, threshold=0.8, return_score=False, force_coeff=False, min_scale=0.05, max_scale=1.5, crop_template=False):
    import cv2
    if not os.path.exists(template_path):
        if return_score:
            return False, 0.0
        return False
        
    template = brief_service.get_cached_image(str(template_path))
    if template is None:
        if return_score:
            return False, 0.0
        return False
        
    if crop_template:
        template = template.copy()
        if len(template.shape) == 3:
            gray_tmpl = cv2.cvtColor(template[:, :, :3], cv2.COLOR_BGR2GRAY)
        else:
            gray_tmpl = template
        _, thresh = cv2.threshold(gray_tmpl, 180, 255, cv2.THRESH_BINARY)
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        x_min, y_min = template.shape[1], template.shape[0]
        x_max, y_max = 0, 0
        for c in contours:
            x, y, w, h = cv2.boundingRect(c)
            if w > 10 and h > 10:
                x_min = min(x_min, x)
                y_min = min(y_min, y)
                x_max = max(x_max, x + w)
                y_max = max(y_max, y + h)
        if x_max > x_min and y_max > y_min:
            template = template[y_min:y_max, x_min:x_max]
        
    has_alpha = False
    if len(template.shape) == 3 and template.shape[2] == 4:
        if force_coeff:
            alpha = template[:, :, 3:4] / 255.0
            bgr = template[:, :, :3]
            gray_tmpl = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
            bg_color = 255 if gray_tmpl.mean() > 127 else 0
            template = (bgr * alpha + np.ones_like(bgr) * bg_color * (1 - alpha)).astype(np.uint8)
            template_mask = None
        else:
            has_alpha = True
            template_mask = template[:, :, 3]
            template = cv2.cvtColor(template, cv2.COLOR_BGRA2BGR)
            threshold = max(threshold, 0.75) # CCORR_NORMED can be more generous, so bump threshold
    else:
        template_mask = None
        
    # Dynamic Pass 1 scaling to support tiny scales down to min_scale without shrinking templates below 10px
    total_min_scale = min_scale
    total_max_scale = max_scale
    min_template_dim = min(template.shape[0], template.shape[1])
    
    min_tiny_dim_at_min_scale = min_template_dim * total_min_scale
    pass1_fx = 0.125
    if min_tiny_dim_at_min_scale * pass1_fx < 10.0:
        pass1_fx = max(0.125, min(0.5, 10.0 / min_tiny_dim_at_min_scale))
        
    if pass1_fx > 0.25:
        pass1_fx = 0.5
    elif pass1_fx > 0.125:
        pass1_fx = 0.25
        
    tiny_img = cv2.resize(image_np, (0, 0), fx=pass1_fx, fy=pass1_fx)
    tiny_template = cv2.resize(template, (0, 0), fx=pass1_fx, fy=pass1_fx, interpolation=cv2.INTER_AREA)
    if has_alpha:
        tiny_mask = cv2.resize(template_mask, (0, 0), fx=pass1_fx, fy=pass1_fx, interpolation=cv2.INTER_AREA)
        
    best_total_scale_rough = 1.0
    best_val_rough = -1.0
    
    # Search with 18 steps from total_min_scale to total_max_scale for high speed
    for total_scale in np.linspace(total_min_scale, total_max_scale, 18):
        w = int(tiny_template.shape[1] * total_scale)
        h = int(tiny_template.shape[0] * total_scale)
        if w < 10 or h < 10 or w > tiny_img.shape[1] or h > tiny_img.shape[0]: continue
        
        rt = cv2.resize(tiny_template, (w, h), interpolation=cv2.INTER_AREA)
        if has_alpha:
            rm = cv2.resize(tiny_mask, (w, h), interpolation=cv2.INTER_AREA)
            res = cv2.matchTemplate(tiny_img, rt, cv2.TM_CCORR_NORMED, mask=rm)
        else:
            res = cv2.matchTemplate(tiny_img, rt, cv2.TM_CCOEFF_NORMED)
            
        _, max_val, _, _ = cv2.minMaxLoc(res)
        if max_val > best_val_rough:
            best_val_rough = max_val
            best_total_scale_rough = total_scale
            
    # Pass 2: Search at 0.25 scale or higher (must match Pass 1 minimum scale resolution)
    pass2_fx = max(0.25, pass1_fx)
    small_image = cv2.resize(image_np, (0, 0), fx=pass2_fx, fy=pass2_fx)
    small_template = cv2.resize(template, (0, 0), fx=pass2_fx, fy=pass2_fx, interpolation=cv2.INTER_AREA)
    if has_alpha:
        small_mask = cv2.resize(template_mask, (0, 0), fx=pass2_fx, fy=pass2_fx, interpolation=cv2.INTER_AREA)
        
    best_max_val = -1.0
    # Use a dense grid of 13 scales around best_total_scale_rough to prevent integer-rounding aspect-ratio mismatches
    scales_to_check = np.linspace(best_total_scale_rough * 0.85, best_total_scale_rough * 1.15, 13)
    
    for total_scale in scales_to_check:
        w = int(small_template.shape[1] * total_scale)
        h = int(small_template.shape[0] * total_scale)
        if w < 10 or h < 10 or w > small_image.shape[1] or h > small_image.shape[0]: continue
        
        rt = cv2.resize(small_template, (w, h), interpolation=cv2.INTER_AREA)
        if has_alpha:
            rm = cv2.resize(small_mask, (w, h), interpolation=cv2.INTER_AREA)
            res = cv2.matchTemplate(small_image, rt, cv2.TM_CCORR_NORMED, mask=rm)
        else:
            res = cv2.matchTemplate(small_image, rt, cv2.TM_CCOEFF_NORMED)
            
        _, max_val, _, _ = cv2.minMaxLoc(res)
        if max_val > best_max_val:
            best_max_val = max_val
            
    msg = f"[CV DEBUG] match_template: path={template_path} crop={crop_template} best_max_val={best_max_val:.4f} threshold={threshold} matched={best_max_val >= threshold}\n"
    try:
        with open("/tmp/vito_error.log", "a") as f:
            f.write(msg)
    except:
        pass
    print(msg.strip(), flush=True)
    if return_score:
        return best_max_val >= threshold, best_max_val
    return best_max_val >= threshold

@app.post("/api/v1/brief/upload", response_model=UploadBriefResponse)
async def upload_brief(file: UploadFile = File(...)):
    return await brief_service.process_upload_brief(file)

@app.post("/api/v1/clear-qa-assets", response_model=ClearAssetsResponse)
async def clear_qa_assets():
    return brief_service.process_clear_qa_assets()

@app.get("/api/v1/debug-assets", response_model=DebugAssetsResponse)
def debug_assets():
    return brief_service.process_debug_assets()

@app.post("/api/v1/analyze-elements")
def analyze_elements(req: AnalyzeFrameRequest):
    import time
    start_time = time.time()
    try:
        # Decode base64 image
        img_data = base64.b64decode(req.image_base64.split(',')[1] if ',' in req.image_base64 else req.image_base64)
        nparr = np.frombuffer(img_data, np.uint8)
        img_np = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img_np is None:
            print("ERROR [analyze_elements]: cv2.imdecode returned None for provided image_base64.")
            raise HTTPException(status_code=400, detail="Nie udało się wczytać przesłanej klatki z wideo. Zdekodowany obraz jest uszkodzony lub ma nieobsługiwany format.")
        
        # 1. Parsowanie nazwy pliku
        try:
            metadata = parse_filename(req.filename)
            lang_code = metadata['language']
            dimension = metadata['dimension']
        except ParserError as e:
            # Rzucamy błąd (Guardrail)
            raise HTTPException(status_code=400, detail=str(e))
            
        # Zabezpieczenie: jeśli wymiar to np. 1080x1080 to mapujemy to na '1x1' by dopasować do struktury folderów BONG
        # Prosta logika mapująca (można rozbudować)
        dim_map = {"1080x1080": "1x1", "1920x1080": "16x9", "1080x1920": "9x16", "4K": "16x9"}
        bong_dim = dim_map.get(dimension, "16x9")
            
        # 2. Parsowanie Briefu i Cache
        brief_path = str(state.UPLOAD_DIR / "current_brief.xlsx")
        if not os.path.exists(brief_path):
            raise HTTPException(status_code=400, detail="Błąd krytyczny QA: Brak wgranego Briefu! Wgraj najpierw plik LOC Brief (.xlsx).")
            
        cv_assets_dir = Path(settings.cv_assets_path)
        if not cv_assets_dir.exists():
            raise HTTPException(
                status_code=400,
                detail=f"Błąd krytyczny: Dysk sieciowy z bazą CV_Assets jest niedostępny (sprawdź ścieżkę: {cv_assets_dir}). Sprawdź połączenie sieciowe lub konfigurację .env."
            )
            
        sheet_name = lang_code if "-" in lang_code else f"{lang_code}-{lang_code}"
        
        # Get everything from cache
        try:
            reqs, icon_bytes, best_db_path = brief_service.get_cached_brief_data(brief_path, sheet_name, cv_assets_dir)
        except ParserError as e:
            raise HTTPException(status_code=400, detail=str(e))
            
        rating_org = reqs.get("RATING", "PEGI")
        RATING_ORG_MAP = {"SEGOB": "MX", "CLASSIND": "BR", "GRAC": "KR", "OFLC": "AUS"}
        mapped_org = RATING_ORG_MAP.get(rating_org.upper(), rating_org)
        rating_folder = cv_assets_dir / "RATINGS" / mapped_org
            
        rating_age = reqs.get("AGE", "18")
        bong_type = reqs.get("BONG", "Standard")
        bing_type = reqs.get("BING", "Standard")
        
        rating_paths_to_check = []
        brief_rating_b64 = None
        
        # 1. Próba wyciągnięcia i dopasowania ikony z briefu
        if icon_bytes:
            brief_rating_b64 = "data:image/png;base64," + base64.b64encode(icon_bytes).decode("utf-8")
            if best_db_path:
                rating_paths_to_check = [best_db_path]
                
                # Dodaj powiązane szablony o tym samym wieku i pasującym do wideo formacie (np. 9x16 lub 1x1)
                video_ar = "16x9"
                if req.filename:
                    fname = req.filename.upper()
                    if "9X16" in fname or "9:16" in fname or "1080X1920" in fname:
                        video_ar = "9x16"
                    elif "1X1" in fname or "1:1" in fname or "1080X1080" in fname:
                        video_ar = "1x1"
                
                age_str = str(rating_age).upper()
                age_patterns = [age_str]
                if age_str == "T": age_patterns += ["TEEN"]
                elif age_str == "E": age_patterns += ["EVERYONE"]
                
                if rating_folder.exists():
                    for f in rating_folder.glob("*_cropped.png"):
                        comp_name = f.name.upper()
                        if not any(pat in comp_name for pat in age_patterns):
                            continue
                        
                        base = f.name.replace('_cropped.png', '').replace('.png', '')
                        tokens = [t.upper() for t in base.split('_')]
                        
                        age_patterns_tokens = [str(x).upper() for x in age_patterns]
                        if not any(pat in tokens for pat in age_patterns_tokens):
                            continue
                            
                        matches_ar = False
                        if video_ar == "9x16" and "9X16" in comp_name:
                            matches_ar = True
                        elif video_ar == "1x1" and "1X1" in comp_name:
                            matches_ar = True
                        elif video_ar == "16x9" and ("16X9" in comp_name or "4K" in comp_name or not any(x in comp_name for x in ["9X16", "1X1"])):
                            matches_ar = True
                            
                        if matches_ar and str(f) not in rating_paths_to_check:
                            rating_paths_to_check.append(str(f))
                
        # 2. Fallback na tekstowe wyszukiwanie, jeśli ikony brak lub ORB nie dopasował
        if not rating_paths_to_check and rating_folder.exists():
            for f in rating_folder.glob("*_cropped.png"):
                name_upper = f.name.upper()
                
                # Filter ESRB templates based on language/region
                if rating_org == "ESRB":
                    is_french = "FR" in lang_code.upper()
                    is_spanish = "ES" in lang_code.upper() or "LATAM" in lang_code.upper()
                    
                    if is_french and not any(x in name_upper for x in ["FR", "FRENCH", "FRE", "CA", "BILINGUAL", "ET "]):
                        continue
                    if is_spanish and not any(x in name_upper for x in ["SP", "SPANISH", "LATAM"]):
                        continue
                    if not is_french and not is_spanish and any(x in name_upper for x in ["FR", "FRENCH", "FRE", "SP", "SPANISH", "LATAM"]):
                        continue

                # Strict matching to avoid E-T, T-M, ToTeen, etc.
                if rating_org == "ESRB":
                    if rating_age == "T":
                        if ("_T_" in name_upper or "TEEN_" in name_upper or "ESRB_T" in name_upper or "ESRB_2013_TEEN" in name_upper or "BILINGUAL" in name_upper) and not any(x in name_upper for x in ["T-M", "E-T", "TOTEEN", "TOMATURE"]):
                            rating_paths_to_check.append(str(f))
                    elif rating_age == "E":
                        if ("_E_" in name_upper or "EVERYONE_" in name_upper or "ESRB_E" in name_upper) and not any(x in name_upper for x in ["E-T", "E-M", "E10", "TOEVERYONE"]):
                            rating_paths_to_check.append(str(f))
                    elif rating_age == "E10+":
                        if ("E10" in name_upper or "EVERYONE10" in name_upper) and not any(x in name_upper for x in ["TOEVERYONE", "TOADULTS"]):
                            rating_paths_to_check.append(str(f))
                    elif rating_age == "M":
                        if ("_M_" in name_upper or "MATURE_" in name_upper or "ESRB_M" in name_upper) and not any(x in name_upper for x in ["T-M", "E-M", "TOMATURE"]):
                            rating_paths_to_check.append(str(f))
                    else:
                        if str(rating_age).upper() in name_upper:
                            rating_paths_to_check.append(str(f))
                else:
                    # Exact match pattern for ratings (e.g. _B15_, _M_, _18_)
                    if f"_{str(rating_age).upper()}_" in name_upper:
                        rating_paths_to_check.append(str(f))
                        
        # Get aspect ratio of the incoming video
        bong_dim = "16x9"
        if req.filename:
            fname = req.filename.upper()
            if "9X16" in fname or "9:16" in fname or "1080X1920" in fname:
                bong_dim = "9x16"
            elif "1X1" in fname or "1:1" in fname or "1080X1080" in fname:
                bong_dim = "1x1"
            elif "16X9" in fname or "16:9" in fname or "1920X1080" in fname or "3840X2160" in fname:
                bong_dim = "16x9"
                
        # Bong path logic
        bong_lang = lang_code
        if "-" in lang_code:
            bong_lang = lang_code.split("-")[1]
            
        VALID_BONG_LANGS = ["AR", "EN_R", "EN_TM", "ES", "ES_R", "FR", "FR_ALT", "JA", "PT", "RU", "TR", "UA", "ZH"]
        
        phnl_val = str(reqs.get("PHNL", "")).upper().strip()
        
        paths_to_check = []
        is_universal = False
        
        # If it's explicitly 'STANDARD' or similar, we consider it universal (or what does standard/localized mean?)
        if phnl_val == "STANDARD" or phnl_val == "NO" or "US (MASTER)" in phnl_val or "ENGLISH" in phnl_val:
            is_universal = True
        elif bong_lang not in VALID_BONG_LANGS:
            is_universal = True
            
        if is_universal:
            for univ_lang in ["EN_R", "EN_TM"]:
                cp = cv_assets_dir / "BONG" / bong_dim / univ_lang / "shot1_cropped.png"
                sp = cv_assets_dir / "BONG" / bong_dim / univ_lang / "shot1.png"
                paths_to_check.append(str(cp if cp.exists() else sp))
        else:
            cp = cv_assets_dir / "BONG" / bong_dim / bong_lang / "shot1_cropped.png"
            sp = cv_assets_dir / "BONG" / bong_dim / bong_lang / "shot1.png"
            paths_to_check.append(str(cp if cp.exists() else sp))
            
        # Bing path logic
        bing_cropped = cv_assets_dir / "BING" / bong_dim / "Universal" / "shot1_cropped.png"
        bing_std = cv_assets_dir / "BING" / bong_dim / "Universal" / "shot1.png"
        bing_path = str(bing_cropped if bing_cropped.exists() else bing_std)
            
        # 4. Wykonanie Computer Vision (Template Matching)
        
        is_start = req.timestamp is None or req.timestamp <= 4.0
        
        # Determine if it's the end of the video based on parsed duration
        is_end = False
        if req.timestamp is None:
            is_end = True
        else:
            # Parse duration from filename (e.g. 06s, 15s, 30s)
            vid_duration = 30.0 # Default fallback
            if req.filename:
                import re
                dur_match = re.search(r'_(\d+)s', req.filename.upper())
                if dur_match:
                    try:
                        vid_duration = float(dur_match.group(1))
                    except:
                        pass
            
            # If the timestamp is near the end, check BONG
            if req.timestamp >= (vid_duration - 2.0):
                is_end = True
            elif req.timestamp >= 10.0:
                is_end = True
        
        # Ogranicz obszar poszukiwań ratingu do dolnej połowy ekranu dla poziomego wideo (16x9).
        # Dla pionowego (9x16) lub kwadratowego (1x1) przeszukujemy cały ekran, gdyż rating może być na środku.
        is_vertical_or_square = False
        if req.filename:
            fname = req.filename.upper()
            if any(x in fname for x in ["9X16", "9:16", "1080X1920", "1X1", "1:1", "1080X1080"]):
                is_vertical_or_square = True
                
        if is_vertical_or_square:
            img_rating = img_np
        else:
            h_orig = img_np.shape[0]
            img_rating = img_np[int(h_orig * 0.5):, :]
        
        best_allowed_score = 0
        best_allowed_path = None
        has_rating = False
        
        # Testujemy wszystkie dozwolone szablony
        allowed_results = []
        for rp in rating_paths_to_check:
            try:
                tmp_img = brief_service.get_cached_image(rp)
                th = tmp_img.shape[0] if tmp_img is not None else 800
            except:
                th = 800
            min_sc = max(0.02, 40.0 / th)
            max_sc = min(1.5, 300.0 / th)
            matched, score = match_template(img_rating, rp, return_score=True, force_coeff=False, min_scale=min_sc, max_scale=max_sc)
            if score > 0.4:
                try:
                    tmp_img = brief_service.get_cached_image(rp)
                    ar = tmp_img.shape[1] / float(tmp_img.shape[0]) if tmp_img is not None else 1.0
                except:
                    ar = 1.0
                allowed_results.append((score, ar, rp))
                
        if allowed_results:
            allowed_results.sort(key=lambda x: x[0], reverse=True)
            best_allowed_score = allowed_results[0][0]
            best_allowed_path = allowed_results[0][2]
            
            # Prefer vertical/square generic templates over wide templates with descriptors if scores are close
            for score, ar, rp in allowed_results:
                if score >= best_allowed_score - 0.12 and score >= 0.65:
                    if ar <= 1.25 and allowed_results[0][1] > 1.4:
                        best_allowed_score = score
                        best_allowed_path = rp
                        break
                
        # Zmieniony próg dla TM_CCOEFF_NORMED (z 0.8 na 0.72)
        # Zmieniony próg dla TM_CCOEFF_NORMED (z 0.8 na 0.72)
        if best_allowed_score >= 0.72:
            rating_status = "FOUND"
            has_rating = True
            rating_path_used = best_allowed_path
            
            # Weryfikacja wariantu: sprawdź czy inny szablon tego samego typu
            # nie pasuje lepiej (np. angielski zamiast francuskiego)
            if is_start and len(rating_paths_to_check) <= 1:
                best_competitor_score = 0
                best_competitor_path = None
                
                exp_name = os.path.basename(best_allowed_path).upper()
                exp_is_fr_sp = any(x in exp_name for x in ["FR", "FRENCH", "CA", "BILINGUAL", "SP", "SPANISH", "LATAM"])
                
                # Przeszukujemy szablony z bazy o tej samej kategorii wiekowej
                age_str = str(rating_age).upper()
                age_patterns = [age_str]
                if age_str == "T":
                    age_patterns += ["TEEN"]
                elif age_str == "E":
                    age_patterns += ["EVERYONE"]
                elif age_str == "M":
                    age_patterns += ["MATURE"]
                elif age_str == "E10+":
                    age_patterns += ["E10", "EVERYONE10"]
                
                for f in rating_folder.glob("*_cropped.png"):
                    comp_name = f.name.upper()
                    if comp_name == exp_name:
                        continue
                        
                    # Dopasuj tylko szablony tej samej kategorii wiekowej
                    if not any(pat in comp_name for pat in age_patterns):
                        continue
                        
                    comp_is_fr_sp = any(x in comp_name for x in ["FR", "FRENCH", "CA", "BILINGUAL", "SP", "SPANISH", "LATAM"])
                    # Porównujemy tylko warianty obcojęzyczne (np. FR vs EN)
                    if exp_is_fr_sp != comp_is_fr_sp:
                        try:
                            tmp_img = brief_service.get_cached_image(str(f))
                            th = tmp_img.shape[0] if tmp_img is not None else 800
                        except:
                            th = 800
                        min_sc = max(0.02, 40.0 / th)
                        max_sc = min(1.5, 300.0 / th)
                        _, c_score = match_template(img_rating, str(f), return_score=True, force_coeff=False, min_scale=min_sc, max_scale=max_sc)
                        if c_score > best_competitor_score:
                            best_competitor_score = c_score
                            best_competitor_path = str(f)
                
                if best_competitor_score > best_allowed_score + 0.05:
                    rating_status = "INCORRECT"
                    has_rating = False
                    rating_path_used = best_competitor_path
        else:
            # Nie znaleziono oczekiwanego - szukamy jakiegokolwiek innego, by zgłosić INCORRECT
            best_generic_score = 0
            best_generic_path = None
            if rating_folder.exists() and is_start:
                generic_paths = [str(p) for p in rating_folder.glob("*_cropped.png") if ("_M_" in p.name or "_T_" in p.name or "_E_" in p.name or "18" in p.name or "16" in p.name or "12" in p.name)]
                for gp in generic_paths[:10]:
                    if gp in rating_paths_to_check:
                        continue
                    try:
                        tmp_img = brief_service.get_cached_image(gp)
                        th = tmp_img.shape[0] if tmp_img is not None else 800
                    except:
                        th = 800
                    min_sc = max(0.02, 40.0 / th)
                    max_sc = min(1.5, 300.0 / th)
                    matched, score = match_template(img_rating, gp, return_score=True, force_coeff=False, min_scale=min_sc, max_scale=max_sc)
                    if score > best_generic_score:
                        best_generic_score = score
                        best_generic_path = gp
            
            if best_generic_score >= 0.72:
                rating_status = "INCORRECT"
                has_rating = False
                rating_path_used = best_generic_path
            else:
                rating_status = "MISSING"
                has_rating = False
                rating_path_used = None

        has_bing = match_template(img_np, bing_path, crop_template=True)
        bing_status = "FOUND" if has_bing else "MISSING"
        if not has_bing and is_start:
            pss_bing = cv_assets_dir / "BING" / bong_dim / "PS Studios" / "shot1_cropped.png"
            if pss_bing.exists() and match_template(img_np, str(pss_bing), crop_template=True):
                bing_status = "INCORRECT"
                
        has_bong = False
        for bp in paths_to_check:
            if match_template(img_np, bp):
                has_bong = True
                break
                
        is_6s = req.filename and ("06S" in req.filename.upper() or "_6S" in req.filename.upper() or "-6S" in req.filename.upper())
        
        if is_6s:
            if has_bong:
                bong_status = "FOUND_IN_6S"
            else:
                bong_status = "CORRECT_NO_BONG"
                if req.timestamp is not None and req.timestamp >= 4.5:
                    mean_val = cv2.mean(img_np)[0]
                    if mean_val < 10:
                        bong_status = "BLACK_FRAME_6S"
        else:
            bong_status = "FOUND" if has_bong else "MISSING"
        bong_path_used = next((bp for bp in paths_to_check if match_template(img_np, bp)), None)

        # Prepare base64 images of expected templates
        expected_rating_b64 = brief_service.get_base64_from_path(rating_paths_to_check[0] if rating_paths_to_check else None)
        found_rating_b64 = brief_service.get_base64_from_path(rating_path_used) if rating_path_used else None
        
        expected_bong_b64 = brief_service.get_base64_from_path(paths_to_check[0] if paths_to_check else None)
        found_bong_b64 = brief_service.get_base64_from_path(bong_path_used) if bong_path_used else None
        
        expected_bing_b64 = brief_service.get_base64_from_path(bing_path)
        found_bing_b64 = brief_service.get_base64_from_path(bing_path) if has_bing else None
        
        # Debug: Save frames if something is missing
        if not (has_rating and has_bing and has_bong):
            import time
            ts = int(time.time())
            cv2.imwrite(f"/tmp/debug_frame_{ts}.png", img_np)
            try:
                with open("/tmp/vito_error.log", "a") as f:
                    f.write(f"Zapisano klatkę do /tmp/debug_frame_{ts}.png\n")
            except Exception:
                pass
            print(f"DEBUG: Zapisano klatkę do /tmp/debug_frame_{ts}.png")
        
        return {
            "success": True, 
            "metadata_used": {"language": lang_code, "dimension": dimension, "expected_requirements": reqs},
            "rating": rating_status, 
            "bing": bing_status, 
            "bong": bong_status,
            "brief_rating_b64": brief_rating_b64,
            "expected_rating_b64": expected_rating_b64,
            "found_rating_b64": found_rating_b64,
            "expected_bing_b64": expected_bing_b64,
            "found_bing_b64": found_bing_b64,
            "expected_bong_b64": expected_bong_b64,
            "found_bong_b64": found_bong_b64
        }
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        err_str = traceback.format_exc()
        try:
            with open("/tmp/vito_error.log", "a") as f:
                f.write(err_str + "\n")
        except Exception:
            pass
        print(err_str)
        return {"success": False, "error": str(e)}


@app.post("/api/v1/copydeck/parse", response_model=CopydeckParseResponse)
async def parse_copydeck(file: UploadFile = File(...)):
    ext = Path(file.filename).suffix.lower()
    if ext not in [".xlsx", ".xls"]:
        raise HTTPException(status_code=422, detail=f"Niedozwolony format pliku: {ext}. Wymagany: .xlsx lub .xls")
        
    return await process_copydeck_file(file)

# --- Static Frontend Serving for Standalone App ---
frontend_dist = Path(__file__).parent.parent / "frontend_dist"
if not frontend_dist.exists():
    # Fallback for dev mode
    frontend_dist = Path(__file__).parent.parent / "frontend" / "dist"

if frontend_dist.exists() and (frontend_dist / "index.html").exists():
    assets_dir = frontend_dist / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

    @app.get("/{file_path:path}")
    async def serve_static(file_path: str):
        if file_path == "":
            return HTMLResponse(
                (frontend_dist / "index.html").read_text(),
                headers={"Cache-Control": "no-cache, no-store, must-revalidate"}
            )
        
        target = frontend_dist / file_path
        if target.exists() and target.is_file():
            return FileResponse(target)
        
        # Fallback to index.html for SPA routing
        return HTMLResponse(
            (frontend_dist / "index.html").read_text(),
            headers={"Cache-Control": "no-cache, no-store, must-revalidate"}
        )
