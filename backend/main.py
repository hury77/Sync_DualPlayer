from fastapi import FastAPI, UploadFile, File, Form, HTTPException, BackgroundTasks, Request
from fastapi.responses import JSONResponse, StreamingResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
import os
import uuid
import subprocess
import asyncio
import re
from pathlib import Path

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

def transcode_to_mp4(input_path: Path, output_path: Path, file_id: int):
    """Automatically transcodes ProRes/MOV/MXF to H.264 MP4 for web playback."""
    try:
        cmd = [
            "ffmpeg",
            "-y",
            "-i", str(input_path),
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "23",
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
        if process.returncode == 0:
            if file_id in files_db:
                files_db[file_id]["is_processed"] = True
                files_db[file_id]["proxy_path"] = str(output_path)
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
    
    with open(file_path, "wb") as buffer:
        while chunk := await file.read(8192):
            buffer.write(chunk)
            
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
            "transcode_progress": f["progress"]
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
