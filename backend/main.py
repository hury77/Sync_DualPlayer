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


class AnalyzeFrameRequest(BaseModel):
    image_base64: str
    country_code: str

def match_template(image_np, template_path, threshold=0.7):
    if not os.path.exists(template_path):
        return False
    template = cv2.imread(template_path, cv2.IMREAD_COLOR)
    if template is None:
        return False
    # Resize template if it's larger than image
    if template.shape[0] > image_np.shape[0] or template.shape[1] > image_np.shape[1]:
        return False
    res = cv2.matchTemplate(image_np, template, cv2.TM_CCOEFF_NORMED)
    loc = np.where(res >= threshold)
    if len(loc[0]) > 0:
        return True
    return False

@app.post("/api/v1/analyze-elements")
async def analyze_elements(req: AnalyzeFrameRequest):
    try:
        # Decode base64 image
        img_data = base64.b64decode(req.image_base64.split(',')[1] if ',' in req.image_base64 else req.image_base64)
        nparr = np.frombuffer(img_data, np.uint8)
        img_np = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        # Determine expected templates based on country code
        # Mock logic based on Plan
        rating_path = 'backend/templates/ratings/esrb_teen.png'
        if 'UK' in req.country_code or 'PL' in req.country_code:
            rating_path = 'backend/templates/ratings/pegi_18.png'
            
        bing_path = 'backend/templates/bings/ps_logo.png'
        
        bong_path = 'backend/templates/bongs/standard.png'
        if 'FR' in req.country_code:
            bong_path = 'backend/templates/bongs/french.png'
            
        has_rating = match_template(img_np, rating_path)
        has_bing = match_template(img_np, bing_path)
        has_bong = match_template(img_np, bong_path)
        
        return {"success": True, "rating": has_rating, "bing": has_bing, "bong": has_bong}
    except Exception as e:
        print(e)
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
