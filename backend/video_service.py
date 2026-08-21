import os
import re
import time
import shutil
import asyncio
import uuid
import subprocess
import imageio_ffmpeg
from pathlib import Path
from fastapi import BackgroundTasks, UploadFile, HTTPException
from fastapi.responses import FileResponse
import state

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
            "-b:v", "15M",
            "-q:v", "60",
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
                    if file_id in state.files_db:
                        state.files_db[file_id]["progress"] = progress
        
        process.wait()
        end_time = time.time()
        conversion_time = round(end_time - start_time, 2)
        
        if process.returncode == 0:
            if file_id in state.files_db:
                state.files_db[file_id]["is_processed"] = True
                state.files_db[file_id]["proxy_path"] = str(output_path)
                state.files_db[file_id]["conversion_time"] = conversion_time
        else:
            if file_id in state.files_db:
                state.files_db[file_id]["processing_error"] = "FFmpeg failed to transcode"
                
    except Exception as e:
        if file_id in state.files_db:
            state.files_db[file_id]["processing_error"] = str(e)


async def process_video_upload(background_tasks: BackgroundTasks, file: UploadFile) -> dict:
    ext = Path(file.filename).suffix.lower()
    
    file_id = state.file_counter
    state.file_counter += 1
    
    random_str = str(uuid.uuid4())[:8]
    safe_filename = f"{Path(file.filename).stem}_{random_str}{ext}"
    file_path = state.UPLOAD_DIR / safe_filename
    
    state.files_db[file_id] = {
        "id": file_id,
        "filename": file.filename,
        "path": str(file_path),
        "is_processed": False,
        "processing_error": None,
        "progress": 0,
        "proxy_path": None
    }
    
    loop = asyncio.get_running_loop()
    def save_file():
        try:
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
        except Exception as e:
            print(f"CRITICAL ERROR [save_file]: Failed to write file stream to disk: {e}")
            if file_id in state.files_db:
                state.files_db[file_id]["processing_error"] = "Nie udało się zapisać przesłanego pliku wideo. Upewnij się, że dysk serwera nie jest pełny."
                state.files_db[file_id]["is_processed"] = True
    await loop.run_in_executor(None, save_file)
            
    # If not mp4/webm, we must transcode
    if ext not in [".mp4", ".webm"]:
        proxy_path = state.UPLOAD_DIR / f"{Path(file.filename).stem}_{random_str}_proxy.mp4"
        background_tasks.add_task(transcode_to_mp4, file_path, proxy_path, file_id)
    else:
        state.files_db[file_id]["is_processed"] = True
        state.files_db[file_id]["proxy_path"] = str(file_path)
        
    return {"file_id": file_id}


def get_status(file_id: int) -> dict:
    if file_id not in state.files_db:
        raise HTTPException(status_code=404, detail="File not found")
        
    f = state.files_db[file_id]
    return {
        "is_processed": f["is_processed"],
        "processing_error": f["processing_error"],
        "file_metadata": {
            "transcode_progress": f.get("progress"),
            "conversion_time": f.get("conversion_time")
        }
    }


def get_file_stream(file_id: int) -> FileResponse:
    if file_id not in state.files_db:
        raise HTTPException(status_code=404, detail="File not found")
        
    f = state.files_db[file_id]
    if not f["is_processed"] or not f["proxy_path"]:
        raise HTTPException(status_code=400, detail="File not processed yet")
        
    file_path = f["proxy_path"]
    
    return FileResponse(file_path, media_type="video/mp4", headers={"Accept-Ranges": "bytes"})


def delete_file(file_id: int) -> dict:
    if file_id not in state.files_db:
        return {"status": "ignored", "detail": "File not found"}
        
    f = state.files_db[file_id]
    
    # Usuwamy plik źródłowy
    try:
        if f.get("path") and os.path.exists(f["path"]):
            os.remove(f["path"])
    except Exception as e:
        print(f"CRITICAL ERROR [delete_file]: Failed to remove file {f.get('path')}: {e}")
        raise HTTPException(status_code=500, detail="Nie udało się usunąć pliku wideo. Sprawdź, czy plik nie jest używany przez inny proces. Jeśli problem się powtarza, skontaktuj się z administratorem.")
        
    # Usuwamy plik proxy (jeśli istnieje i jest inny niż źródłowy)
    try:
        if f.get("proxy_path") and f.get("proxy_path") != f.get("path") and os.path.exists(f["proxy_path"]):
            os.remove(f["proxy_path"])
    except Exception as e:
        print(f"CRITICAL ERROR [delete_file]: Failed to remove proxy file {f.get('proxy_path')}: {e}")
        raise HTTPException(status_code=500, detail="Nie udało się usunąć pliku wideo. Sprawdź, czy plik nie jest używany przez inny proces. Jeśli problem się powtarza, skontaktuj się z administratorem.")
        
    # Usuwamy wpis z bazy
    del state.files_db[file_id]
    
    return {"status": "ok", "detail": "Files deleted successfully"}
