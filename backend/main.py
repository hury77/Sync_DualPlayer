from fastapi import FastAPI, UploadFile, File, Form, HTTPException, BackgroundTasks, Request
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
from pydantic import BaseModel
from typing import List, Optional
import pandas as pd
import io

app = FastAPI(title="Sync DualPlayer API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

# In-memory database for standalone player
files_db = {}
file_counter = 1

def get_robust_ffmpeg_exe():
    local_ffmpeg = os.path.join(os.path.dirname(__file__), "ffmpeg")
    if os.path.exists(local_ffmpeg):
        return local_ffmpeg

    exe = imageio_ffmpeg.get_ffmpeg_exe()
    if exe == "ffmpeg":
        bundled_dir = os.path.join(os.path.dirname(imageio_ffmpeg.__file__), "binaries")
        if os.path.exists(bundled_dir):
            for f in os.listdir(bundled_dir):
                if "ffmpeg" in f and not f.endswith(".md") and not f.endswith(".py"):
                    return os.path.join(bundled_dir, f)
    return exe

def transcode_to_mp4(input_path: Path, output_path: Path, file_id: int):
    """Automatically transcodes ProRes/MOV/MXF to H.264 MP4 for web playback."""
    start_time = time.time()
    try:
        ffmpeg_exe = get_robust_ffmpeg_exe()
        cmd = [
            ffmpeg_exe,
            "-hwaccel", "auto",
            "-nostdin",
            "-y",
            "-i", str(input_path),
            "-c:v", "h264_videotoolbox",
            "-b:v", "3M",
            "-c:a", "aac",
            "-b:a", "192k",
            "-pix_fmt", "yuv420p",
            "-movflags", "+faststart",
            str(output_path)
        ]
        
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True
        )
        
        duration = 100 # Default to avoid div zero if ffprobe fails
        
        # Read stderr to get progress
        duration_regex = re.compile(r"Duration: (\d{2}):(\d{2}):(\d{2}\.\d{2})")
        time_regex = re.compile(r"time=(\d{2}):(\d{2}):(\d{2}\.\d{2})")
        
        for line in process.stderr:
            if "Duration" in line:
                match = duration_regex.search(line)
                if match:
                    h, m, s = match.groups()
                    duration = int(h) * 3600 + int(m) * 60 + float(s)
            
            if "time=" in line:
                match = time_regex.search(line)
                if match:
                    h, m, s = match.groups()
                    current_time = int(h) * 3600 + int(m) * 60 + float(s)
                    progress = min(100, int((current_time / duration) * 100))
                    if file_id in files_db:
                        files_db[file_id]["progress"] = progress
        
        process.wait()
        end_time = time.time()
        conversion_time = round(end_time - start_time, 2)
        
        if process.returncode == 0:
            if file_id in files_db:
                files_db[file_id]["is_processed"] = True
                files_db[file_id]["proxy_path"] = str(output_path)
                files_db[file_id]["conversion_time"] = conversion_time
        else:
            if file_id in files_db:
                files_db[file_id]["processing_error"] = "FFmpeg failed to transcode"
                
    except Exception as e:
        if file_id in files_db:
            files_db[file_id]["processing_error"] = str(e)


@app.post("/api/v1/files/upload")
async def upload_file(background_tasks: BackgroundTasks, file: UploadFile = File(...), file_type: str = Form(...)):
    global file_counter
    file_id = file_counter
    file_counter += 1
    
    ext = Path(file.filename).suffix.lower()
    random_str = str(uuid.uuid4())[:8]
    safe_filename = f"{Path(file.filename).stem}_{random_str}{ext}"
    file_path = UPLOAD_DIR / safe_filename
    
    loop = asyncio.get_running_loop()
    def save_file():
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    await loop.run_in_executor(None, save_file)
            
    files_db[file_id] = {
        "id": file_id,
        "filename": file.filename,
        "path": str(file_path),
        "is_processed": False,
        "processing_error": None,
        "progress": 0,
        "proxy_path": None
    }
    
    # If not mp4/webm, we must transcode
    if ext not in [".mp4", ".webm"]:
        proxy_path = UPLOAD_DIR / f"{Path(file.filename).stem}_{random_str}_proxy.mp4"
        background_tasks.add_task(transcode_to_mp4, file_path, proxy_path, file_id)
    else:
        files_db[file_id]["is_processed"] = True
        files_db[file_id]["proxy_path"] = str(file_path)
        
    return {"file_id": file_id}

@app.get("/api/v1/files/{file_id}")
async def get_file_status(file_id: int):
    if file_id not in files_db:
        raise HTTPException(status_code=404, detail="File not found")
        
    f = files_db[file_id]
    return {
        "is_processed": f["is_processed"],
        "processing_error": f["processing_error"],
        "file_metadata": {
            "transcode_progress": f.get("progress"),
            "conversion_time": f.get("conversion_time")
        }
    }

@app.get("/api/v1/files/stream/{file_id}")
async def stream_file(request: Request, file_id: int):
    if file_id not in files_db:
        raise HTTPException(status_code=404, detail="File not found")
        
    f = files_db[file_id]
    if not f["is_processed"] or not f["proxy_path"]:
        raise HTTPException(status_code=400, detail="File not processed yet")
        
    file_path = f["proxy_path"]
    
    return FileResponse(file_path, media_type="video/mp4", headers={"Accept-Ranges": "bytes"})

@app.delete("/api/v1/files/{file_id}")
async def delete_file(file_id: int):
    if file_id not in files_db:
        return {"status": "ignored", "detail": "File not found"}
        
    f = files_db[file_id]
    
    # Usuwamy plik źródłowy
    try:
        if f.get("path") and os.path.exists(f["path"]):
            os.remove(f["path"])
    except Exception as e:
        print(f"Error removing file {f.get('path')}: {e}")
        
    # Usuwamy plik proxy (jeśli istnieje i jest inny niż źródłowy)
    try:
        if f.get("proxy_path") and f.get("proxy_path") != f.get("path") and os.path.exists(f["proxy_path"]):
            os.remove(f["proxy_path"])
    except Exception as e:
        print(f"Error removing proxy file {f.get('proxy_path')}: {e}")
        
    # Usuwamy wpis z bazy
    del files_db[file_id]
    
    return {"status": "ok", "detail": "Files deleted successfully"}


from parsers import parse_filename, get_requirements_from_brief, ParserError, extract_rating_icon_from_brief

class AnalyzeFrameRequest(BaseModel):
    image_base64: str
    filename: str
    # Opcjonalnie możemy przyjmować kod kraju z frontendu, ale priorytet ma nazwa pliku
    country_code: Optional[str] = None
    timestamp: Optional[float] = None

_image_cache = {}
_image_cache_lock = threading.Lock()

def get_cached_image(path_str):
    with _image_cache_lock:
        if path_str in _image_cache:
            return _image_cache[path_str]
        img = cv2.imread(path_str, cv2.IMREAD_UNCHANGED)
        if img is not None:
            _image_cache[path_str] = img
        return img

def match_template(image_np, template_path, threshold=0.8, return_score=False, force_coeff=False):
    import cv2
    if not os.path.exists(template_path):
        if return_score:
            return False, 0.0
        return False
        
    template = get_cached_image(str(template_path))
    if template is None:
        if return_score:
            return False, 0.0
        return False
        
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
        
    # Dynamic Pass 1 scaling to support tiny scales down to 0.05 without shrinking templates below 4px
    total_min_scale = 0.05
    total_max_scale = 0.25
    min_template_dim = min(template.shape[0], template.shape[1])
    
    pass1_fx = 0.125
    needed_fx = 4.0 / (min_template_dim * total_min_scale)
    if needed_fx > pass1_fx:
        pass1_fx = max(0.125, min(0.5, needed_fx))
        
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
        scale_in_tiny = total_scale / pass1_fx
        w = int(tiny_template.shape[1] * scale_in_tiny)
        h = int(tiny_template.shape[0] * scale_in_tiny)
        if w < 4 or h < 4 or w > tiny_img.shape[1] or h > tiny_img.shape[0]: continue
        
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
        scale_in_small = total_scale / pass2_fx
        w = int(small_template.shape[1] * scale_in_small)
        h = int(small_template.shape[0] * scale_in_small)
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
            
    if return_score:
        return best_max_val >= threshold, best_max_val
    return best_max_val >= threshold

@app.post("/api/v1/brief/upload")
async def upload_brief(file: UploadFile = File(...)):
    try:
        brief_path = UPLOAD_DIR / "current_brief.xlsx"
        contents = await file.read()
        with open(brief_path, "wb") as f:
            f.write(contents)
        return {"success": True, "message": "Brief uploaded successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def get_base64_from_path(path_str):
    if not path_str or not os.path.exists(path_str):
        return None
    try:
        with open(path_str, "rb") as image_file:
            return "data:image/png;base64," + base64.b64encode(image_file.read()).decode("utf-8")
    except Exception:
        return None

def match_brief_icon_to_db(icon_bytes: bytes, rating_folder: Path, rating_age: str = None):
    """
    Używa algorytmu ORB do dopasowania ikony z briefu do bazy szablonów.
    Zwraca krotkę (najlepsza_sciezka, wynik_dopasowania).
    """
    if not icon_bytes or not rating_folder.exists():
        return None, 0
        
    try:
        brief_img = cv2.imdecode(np.frombuffer(icon_bytes, np.uint8), cv2.IMREAD_COLOR)
        if brief_img is None:
            return None, 0
            
        bh, bw = brief_img.shape[:2]
        
        orb = cv2.ORB_create(nfeatures=500)
        bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
        
        brief_gray = cv2.cvtColor(brief_img, cv2.COLOR_BGR2GRAY)
        kp1, des1 = orb.detectAndCompute(brief_gray, None)
        
        if des1 is None:
            return None, 0
            
        avg_brightness = brief_gray.mean()
        bg_color = 0 if avg_brightness < 128 else 255
        
        best_score = 0
        best_path = None
        
        # Filtrujemy szablony po kategorii wiekowej z briefu, aby unikać podwójnych ratingów
        age_patterns = []
        if rating_age:
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
            if age_patterns:
                base = f.name.replace('_cropped.png', '').replace('.png', '')
                tokens = [t.upper() for t in base.split('_')]
                # Odrzucamy podwójne szablony (np. B-B15 dla B15 lub B) przez dokładne dopasowanie tokenu
                if not any(pat in tokens for pat in age_patterns):
                    continue
            template = get_cached_image(str(f))
            if template is None:
                continue
                
            if len(template.shape) == 3 and template.shape[2] == 4:
                alpha = template[:,:,3:4] / 255.0
                bgr = template[:,:,:3]
                bg = np.ones_like(bgr) * bg_color
                composited = (bgr * alpha + bg * (1 - alpha)).astype(np.uint8)
            else:
                composited = template
                
            resized = cv2.resize(composited, (bw, bh))
            template_gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
            
            kp2, des2 = orb.detectAndCompute(template_gray, None)
            if des2 is None:
                continue
                
            matches = bf.match(des1, des2)
            if len(matches) == 0:
                continue
                
            matches = sorted(matches, key=lambda x: x.distance)
            good = [m for m in matches if m.distance < 50]
            score = len(good) / max(len(kp1), 1)
            
            if score > best_score:
                best_score = score
                best_path = str(f)
                
        return best_path, best_score
    except Exception as e:
        print(f"Błąd podczas match_brief_icon_to_db: {e}")
        return None, 0

_brief_cache = {}
_brief_cache_lock = threading.Lock()

def get_cached_brief_data(brief_path_str: str, sheet_name: str, cv_assets_dir: Path):
    cache_key = f"{brief_path_str}_{sheet_name}"
    mtime = os.path.getmtime(brief_path_str) if os.path.exists(brief_path_str) else 0
    
    with _brief_cache_lock:
        if cache_key in _brief_cache and _brief_cache[cache_key]['mtime'] == mtime:
            return _brief_cache[cache_key]['reqs'], _brief_cache[cache_key]['icon_bytes'], _brief_cache[cache_key]['best_db_path']
        
        reqs = get_requirements_from_brief(brief_path_str, sheet_name)
        
        # Calculate rating folder here
        rating_org = reqs.get("RATING", "PEGI")
        RATING_ORG_MAP = {"SEGOB": "MX", "CLASSIND": "BR", "GRAC": "KR", "OFLC": "AUS"}
        mapped_org = RATING_ORG_MAP.get(rating_org.upper(), rating_org)
        rating_folder = cv_assets_dir / "RATINGS" / mapped_org
        
        icon_bytes = extract_rating_icon_from_brief(brief_path_str, sheet_name)
        best_db_path = None
        if icon_bytes:
            best_db_path, _ = match_brief_icon_to_db(icon_bytes, rating_folder, rating_age=reqs.get("AGE"))
            
        _brief_cache[cache_key] = {
            'mtime': mtime,
            'reqs': reqs,
            'icon_bytes': icon_bytes,
            'best_db_path': best_db_path
        }
        
        return reqs, icon_bytes, best_db_path

@app.post("/api/v1/analyze-elements")
async def analyze_elements(req: AnalyzeFrameRequest):
    import time
    start_time = time.time()
    try:
        # Decode base64 image
        img_data = base64.b64decode(req.image_base64.split(',')[1] if ',' in req.image_base64 else req.image_base64)
        nparr = np.frombuffer(img_data, np.uint8)
        img_np = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
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
        brief_path = str(UPLOAD_DIR / "current_brief.xlsx")
        if not os.path.exists(brief_path):
            raise HTTPException(status_code=400, detail="Błąd krytyczny QA: Brak wgranego Briefu! Wgraj najpierw plik LOC Brief (.xlsx).")
            
        cv_assets_dir = Path("/Volumes/PL-EGplusww/Administrative and corporate files/DEPARTMENTS/QA/VITO/CV_Assets")
        if not cv_assets_dir.exists():
            cv_assets_dir = Path("/Users/hubert.rycaj/Documents/PS_elements/CV_Assets")
            
        sheet_name = lang_code if "-" in lang_code else f"{lang_code}-{lang_code}"
        
        # Get everything from cache
        try:
            reqs, icon_bytes, best_db_path = get_cached_brief_data(brief_path, sheet_name, cv_assets_dir)
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
        
        phnl_localised = str(reqs.get("PHNL LOCK-UP LOCALISED?", "NO")).upper().strip()
        phnl_lang = str(reqs.get("PHNL LANGUAGE", "")).upper().strip()
        
        paths_to_check = []
        is_universal = False
        
        if phnl_localised == "NO" or "US (MASTER)" in phnl_lang or "ENGLISH" in phnl_lang:
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
        is_end = req.timestamp is None or req.timestamp >= 10.0
        
        # Ogranicz obszar poszukiwań ratingu do dolnej połowy ekranu (wyklucza logo PS Studio, itp.)
        h_orig = img_np.shape[0]
        img_rating = img_np[int(h_orig * 0.5):, :]
        
        best_allowed_score = 0
        best_allowed_path = None
        has_rating = False
        
        # Testujemy wszystkie dozwolone szablony
        allowed_results = []
        for rp in rating_paths_to_check:
            matched, score = match_template(img_rating, rp, return_score=True, force_coeff=True)
            if score > 0.4:
                try:
                    tmp_img = get_cached_image(rp)
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
            if is_start and len(rating_paths_to_check) == 1:
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
                        _, c_score = match_template(img_rating, str(f), return_score=True, force_coeff=True)
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
                    matched, score = match_template(img_rating, gp, return_score=True, force_coeff=True)
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

        has_bing = match_template(img_np, bing_path)
        bing_status = "FOUND" if has_bing else "MISSING"
        if not has_bing and is_start:
            pss_bing = cv_assets_dir / "BING" / bong_dim / "PS Studios" / "shot1_cropped.png"
            if pss_bing.exists() and match_template(img_np, str(pss_bing)):
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
        expected_rating_b64 = get_base64_from_path(rating_paths_to_check[0] if rating_paths_to_check else None)
        found_rating_b64 = get_base64_from_path(rating_path_used) if rating_path_used else None
        
        expected_bong_b64 = get_base64_from_path(paths_to_check[0] if paths_to_check else None)
        found_bong_b64 = get_base64_from_path(bong_path_used) if bong_path_used else None
        
        expected_bing_b64 = get_base64_from_path(bing_path)
        found_bing_b64 = get_base64_from_path(bing_path) if has_bing else None
        
        # Debug: Save frames if something is missing
        if not (has_rating and has_bing and has_bong):
            import time
            ts = int(time.time())
            cv2.imwrite(f"/tmp/debug_frame_{ts}.png", img_np)
            with open("/tmp/vito_error.log", "a") as f:
                f.write(f"Zapisano klatkę do /tmp/debug_frame_{ts}.png\n")
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
        with open("/tmp/vito_error.log", "a") as f:
            f.write(err_str + "\n")
        print(err_str)
        return {"success": False, "error": str(e)}


@app.post("/api/v1/copydeck/parse")
async def parse_copydeck(file: UploadFile = File(...)):
    try:
        contents = await file.read()
        
        # Read excel file
        # We try to read it assuming headers might be on row 1 or 2
        # A robust way is to read the whole thing and find the header row containing "Source"
        df = pd.read_excel(io.BytesIO(contents), header=None)
        
        # Find the header row (the one that contains actual language names)
        header_row_idx = 0
        for idx, row in df.iterrows():
            row_str = row.astype(str).str.lower()
            
            # If row contains common language names, it's the right header
            if row_str.str.contains('polish|french|spanish|german|italian|portuguese|english|dutch|swedish|norwegian|danish|finnish').any():
                header_row_idx = idx
                break
                
            # Fallback to 'source' if we haven't found anything better yet
            if row_str.str.contains('source').any() or row_str.str.contains('language').any():
                header_row_idx = idx
                # Do NOT break immediately. The NEXT row might contain the actual languages!
                
        # Re-read with correct header
        df = pd.read_excel(io.BytesIO(contents), header=header_row_idx)
        
        # Clean column names
        df.columns = df.columns.astype(str).str.strip()
        
        # If 'Source' column is not found, take the first column as source
        source_col = None
        for col in df.columns:
            if 'source' in col.lower():
                source_col = col
                break
                
        if not source_col:
            source_col = df.columns[0]
            
        result_dict = {}
        # Iterate over all other columns treating them as languages
        for col in df.columns:
            if col == source_col or 'unnamed' in col.lower():
                continue
                
            # Build dictionary for this language
            lang_dict = {}
            for _, row in df.iterrows():
                src_val = str(row[source_col]).strip() if pd.notna(row[source_col]) else ""
                tgt_val = str(row[col]).strip() if pd.notna(row[col]) else ""
                
                if src_val and tgt_val and src_val.lower() != 'nan' and tgt_val.lower() != 'nan':
                    lang_dict[src_val] = tgt_val
                    
            if lang_dict:
                # Use first line or word as language name if there are multiple lines in header
                clean_col_name = col.split('\\n')[0].split('\\r')[0].strip()
                result_dict[clean_col_name] = lang_dict
                
        return {"success": True, "languages": list(result_dict.keys()), "data": result_dict}
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"success": False, "error": str(e)}

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
