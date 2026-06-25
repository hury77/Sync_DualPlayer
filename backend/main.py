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
            "-vf", "scale=-2:720",
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


from parsers import parse_filename, get_requirements_from_brief, ParserError

class AnalyzeFrameRequest(BaseModel):
    image_base64: str
    filename: str
    # Opcjonalnie możemy przyjmować kod kraju z frontendu, ale priorytet ma nazwa pliku
    country_code: Optional[str] = None

def match_template(image_np, template_path, threshold=0.60):
    if not os.path.exists(template_path):
        return False
    template = cv2.imread(template_path, cv2.IMREAD_UNCHANGED)
    if template is None:
        return False
        
    if len(template.shape) == 3 and template.shape[2] == 4:
        template = cv2.cvtColor(template, cv2.COLOR_BGRA2BGR)
        
    # Downsample by 50% to make matchTemplate 16x faster
    small_image = cv2.resize(image_np, (0, 0), fx=0.5, fy=0.5)
    
    best_max_val = 0
    # Fast multi-scale: only 3 scales (0.8, 1.0, 1.2)
    for scale in [0.8, 1.0, 1.2]: 
        # Calculate new template size (accounting for 50% downsample of the image)
        width = int(template.shape[1] * scale * 0.5)
        height = int(template.shape[0] * scale * 0.5)
        
        if width < 20 or height < 20 or width > small_image.shape[1] or height > small_image.shape[0]:
            continue
            
        resized_template = cv2.resize(template, (width, height), interpolation=cv2.INTER_AREA)
        res = cv2.matchTemplate(small_image, resized_template, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, _ = cv2.minMaxLoc(res)
        
        if max_val > best_max_val:
            best_max_val = max_val
            
    if best_max_val >= threshold:
        return True
    return False

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

@app.post("/api/v1/analyze-elements")
async def analyze_elements(req: AnalyzeFrameRequest):
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
            
        # 2. Parsowanie Briefu by poznać wymagania
        brief_path = str(UPLOAD_DIR / "current_brief.xlsx")
        if not os.path.exists(brief_path):
            raise HTTPException(status_code=400, detail="Błąd krytyczny QA: Brak wgranego Briefu! Wgraj najpierw plik LOC Brief (.xlsx).")
            
        try:
            # W briefie zakładki mają nazwy np. PL-PL, a z pliku wyciągamy np. PL (lub SE-SV)
            # Próbujemy znaleźć dopasowanie w Briefie. Dla testów jeśli kod ma 2 litery, dodajemy resztę np. PL -> PL-PL.
            sheet_name = lang_code if "-" in lang_code else f"{lang_code}-{lang_code}"
            reqs = get_requirements_from_brief(brief_path, sheet_name)
        except ParserError as e:
            raise HTTPException(status_code=400, detail=str(e))
            
        # 3. Budowanie ścieżek do bazy na VITO
        cv_assets_dir = Path("/Volumes/PL-EGplusww/Administrative and corporate files/DEPARTMENTS/QA/VITO/CV_Assets")
        if not cv_assets_dir.exists():
            # Awaryjny fallback na lokalny dysk, jeśli dysk sieciowy nie jest podłączony
            cv_assets_dir = Path("/Users/hubert.rycaj/Documents/PS_elements/CV_Assets")
            
        rating_org = reqs.get("RATING", "PEGI")
        rating_age = reqs.get("AGE", "18")
        bong_type = reqs.get("BONG", "Standard")
        bing_type = reqs.get("BING", "Standard")
        
        # Rating path logic (e.g. RATINGS/PEGI/PEGI_18_cropped.png)
        # To wymaga żeby rating z Excela zgadzał się z nazwami plików. 
        # Na razie szukamy pliku, który w nazwie ma wiek (np. 18, 12, T, M).
        rating_folder = cv_assets_dir / "RATINGS" / rating_org
        rating_path = ""
        if rating_folder.exists():
            for f in rating_folder.glob("*_cropped.png"):
                if str(rating_age) in f.name:
                    rating_path = str(f)
                    break
                    
        # Bong path logic
        bong_path_cropped = cv_assets_dir / "BONG" / bong_dim / lang_code / "shot1_cropped.png"
        bong_path_std = cv_assets_dir / "BONG" / bong_dim / lang_code / "shot1.png"
        bong_shot2_cropped = cv_assets_dir / "BONG" / bong_dim / lang_code / "shot2_cropped.png"
        
        paths_to_check = []
        if bong_path_cropped.exists():
            paths_to_check.append(str(bong_path_cropped))
        elif bong_path_std.exists():
            paths_to_check.append(str(bong_path_std))
        else:
            univ_cropped = cv_assets_dir / "BONG" / bong_dim / "Universal" / "shot1_cropped.png"
            univ_std = cv_assets_dir / "BONG" / bong_dim / "Universal" / "shot1.png"
            paths_to_check.append(str(univ_cropped if univ_cropped.exists() else univ_std))
            
        if bong_shot2_cropped.exists():
            paths_to_check.append(str(bong_shot2_cropped))
        else:
            univ_shot2 = cv_assets_dir / "BONG" / bong_dim / "Universal" / "shot2_cropped.png"
            if univ_shot2.exists():
                paths_to_check.append(str(univ_shot2))
            
        # Bing path logic
        bing_cropped = cv_assets_dir / "BING" / bong_dim / "Universal" / "shot1_cropped.png"
        bing_std = cv_assets_dir / "BING" / bong_dim / "Universal" / "shot1.png"
        bing_path = str(bing_cropped if bing_cropped.exists() else bing_std)
            
        # 4. Wykonanie Computer Vision (Template Matching)
        
        # Rating - sprawdzamy wszystkie pasujące szablony i jeśli jakikolwiek pasuje, to sukces
        has_rating = False
        if rating_folder.exists():
            for f in rating_folder.glob("*_cropped.png"):
                if str(rating_age) in f.name:
                    if match_template(img_np, str(f)):
                        has_rating = True
                        break
                        
        has_bing = match_template(img_np, bing_path)
        
        has_bong = False
        for bp in paths_to_check:
            if match_template(img_np, bp):
                has_bong = True
                break
        
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
            "rating": has_rating, 
            "bing": has_bing, 
            "bong": has_bong
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
