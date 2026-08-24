import os
import cv2
import numpy as np
import pandas as pd
import base64
import re
import io
from pathlib import Path
from fastapi import UploadFile, HTTPException
import state
from config import settings
from parsers import get_requirements_from_brief, extract_rating_icon_from_brief
from copydeck_service import parse_copydeck_from_bytes

def get_cached_image(path_str):
    with state._image_cache_lock:
        if path_str in state._image_cache:
            return state._image_cache[path_str]
        img = cv2.imread(path_str, cv2.IMREAD_UNCHANGED)
        if img is not None:
            state._image_cache[path_str] = img
        return img

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

def get_cached_brief_data(brief_path_str: str, sheet_name: str, cv_assets_dir: Path):
    cache_key = f"{brief_path_str}_{sheet_name}"
    mtime = os.path.getmtime(brief_path_str) if os.path.exists(brief_path_str) else 0
    
    with state._brief_cache_lock:
        if cache_key in state._brief_cache and state._brief_cache[cache_key]['mtime'] == mtime:
            print(f"[CACHE HIT] get_cached_brief_data for {cache_key}", flush=True)
            return state._brief_cache[cache_key]['reqs'], state._brief_cache[cache_key]['icon_bytes'], state._brief_cache[cache_key]['best_db_path']
        
        print(f"[CACHE MISS] get_cached_brief_data for {cache_key} - parsing...", flush=True)
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
            
        state._brief_cache[cache_key] = {
            'mtime': mtime,
            'reqs': reqs,
            'icon_bytes': icon_bytes,
            'best_db_path': best_db_path
        }
        
        return reqs, icon_bytes, best_db_path

async def process_upload_brief(file: UploadFile):
    ext = Path(file.filename).suffix.lower()
    if ext != ".xlsx":
        raise HTTPException(status_code=422, detail="Wgrany plik nie jest prawidłowym plikiem Excel (.xlsx).")
        
    try:
        contents = await file.read()
        
        # Walidacja pliku Excel
        try:
            xl = pd.ExcelFile(io.BytesIO(contents))
            sheets = xl.sheet_names
        except Exception:
            raise HTTPException(status_code=400, detail="Wgrany plik nie jest prawidłowym plikiem Excel (.xlsx).")
            
        if not sheets:
            raise HTTPException(status_code=400, detail="Wgrany plik Excel jest pusty.")
            
        # Wykrywanie Copydecka zamiast Briefu
        if "Extended table" in sheets:
            raise HTTPException(status_code=400, detail="Wgrany plik to prawdopodobnie Copydeck, a nie LOC Brief. Proszę wgrać właściwy plik LOC Brief (.xlsx).")
            
        copydeck_data = None
        copydeck_sheet_name = next((s for s in sheets if s.strip().upper().replace(" ", "") == "COPYDECK"), None)
        if copydeck_sheet_name:
            copydeck_data = parse_copydeck_from_bytes(contents, sheet_name=copydeck_sheet_name)
            
        # Sprawdzanie czy plik ma przynajmniej jedną zakładkę językową (np. FI-FI, PL-PL, JA, AR)
        has_lang_sheet = False
        for s in sheets:
            clean_s = s.strip().upper()
            if re.match(r'^[A-Z]{2}(-[A-Z]{2,4})?$', clean_s) or clean_s in ["JA", "ZH", "KO", "AR", "JA-JA", "KO-KO"]:
                has_lang_sheet = True
                break
                
        if not has_lang_sheet:
            raise HTTPException(
                status_code=400, 
                detail="Wgrany plik nie wygląda na prawidłowy LOC Brief. Brak zakładek językowych (np. FI-FI, CA-FR, PL-PL)."
            )
            
        brief_path = state.UPLOAD_DIR / "current_brief.xlsx"
        with open(brief_path, "wb") as f:
            f.write(contents)
            
        response = {"success": True, "message": "Brief uploaded successfully"}
        if copydeck_data and copydeck_data.get("success"):
            response["copydeck_data"] = copydeck_data
            
        return response
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def process_clear_qa_assets():
    brief_path = state.UPLOAD_DIR / "current_brief.xlsx"
    copydeck_path = state.UPLOAD_DIR / "current_copydeck.xlsx"
    
    with state._brief_cache_lock:
        state._brief_cache.clear()
        
    try:
        if brief_path.exists():
            os.remove(brief_path)
    except Exception as e:
        print(f"CRITICAL ERROR [clear_qa_assets]: Failed to remove brief: {e}")
        raise HTTPException(status_code=500, detail="Nie udało się wyczyścić plików tymczasowych (Brief/Copydeck) na serwerze. Sprawdź, czy zasób nie jest zablokowany, lub skontaktuj się z administratorem.")
        
    try:
        if copydeck_path.exists():
            os.remove(copydeck_path)
    except Exception as e:
        print(f"CRITICAL ERROR [clear_qa_assets]: Failed to remove copydeck: {e}")
        raise HTTPException(status_code=500, detail="Nie udało się wyczyścić plików tymczasowych (Brief/Copydeck) na serwerze. Sprawdź, czy zasób nie jest zablokowany, lub skontaktuj się z administratorem.")
        
    return {"success": True, "message": "LOC Brief and Copydeck cleared successfully"}

def process_debug_assets():
    cv_assets_dir = Path(settings.cv_assets_path)
    bing_std = cv_assets_dir / "BING" / "9x16" / "Universal" / "shot1.png"
    img_imread = cv2.imread(str(bing_std)) if bing_std.exists() else None
    if bing_std.exists() and img_imread is None:
        print(f"ERROR [debug_assets]: cv2.imread returned None for {bing_std}")
        raise HTTPException(status_code=400, detail="Nie udało się wczytać obrazu BING z dysku. Plik może być uszkodzony lub w nieobsługiwanym formacie.")
    
    img_imdecode = None
    imdecode_err = None
    if bing_std.exists():
        try:
            with open(bing_std, "rb") as f:
                b = f.read()
            img_imdecode = cv2.imdecode(np.frombuffer(b, np.uint8), cv2.IMREAD_COLOR)
            if img_imdecode is None:
                print(f"ERROR [debug_assets]: cv2.imdecode returned None for {bing_std}")
                raise HTTPException(status_code=400, detail="Nie udało się zdekodować obrazu BING. Plik bazy może być uszkodzony.")
        except Exception as e:
            imdecode_err = str(e)
            
    return {
        "p1_exists": cv_assets_dir.exists(),
        "cv_assets_dir": str(cv_assets_dir),
        "bing_std_path": str(bing_std),
        "bing_std_exists": bing_std.exists(),
        "bing_imread_loaded": img_imread is not None,
        "bing_imdecode_loaded": img_imdecode is not None,
        "bing_imdecode_shape": img_imdecode.shape if img_imdecode is not None else None,
        "imdecode_err": imdecode_err,
        "current_working_dir": os.getcwd(),
    }
