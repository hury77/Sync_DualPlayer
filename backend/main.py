from fastapi import FastAPI, UploadFile, File, Form, HTTPException, BackgroundTasks, Request, Response
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
import vision_service
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
    if ext not in [".mp4", ".mov", ".mxf", ".gif", ".wav"]:
        raise HTTPException(status_code=422, detail=f"Niedozwolony format pliku: {ext}. Dozwolone: .mp4, .mov, .mxf, .gif, .wav")
        
    return await video_service.process_video_upload(background_tasks, file)

@app.get("/api/v1/files/{file_id}", response_model=FileStatusResponse)
async def get_file_status(file_id: int):
    return video_service.get_status(file_id)

@app.get("/api/v1/files/{file_id}/audio-data")
async def get_audio_data(file_id: int, response: Response):
    if file_id not in state.files_db:
        raise HTTPException(status_code=404, detail="File not found")
        
    analysis = state.files_db[file_id].get("audio_analysis")
    if not analysis:
        # Prawdopodobnie nie uruchomiono jeszcze taska lub z jakiegoś powodu go nie ma
        response.status_code = 202
        return {"status": "processing"}
        
    if analysis["status"] == "processing":
        response.status_code = 202
        return {"status": "processing"}
    elif analysis["status"] == "failed":
        # Ważne: to zwraca 200/202, żeby frontend ładnie sparsował JSON-a z błędem
        return {"status": "failed", "error": analysis["error"]}
    elif analysis["status"] == "completed":
        return {"status": "completed", "data": analysis["data"]}
    else:
        response.status_code = 202
        return {"status": "processing"}

import deep_audio_service
from models import DeepAudioInstallStatus, DeepAudioStatusResponse

@app.post("/api/v1/deep-audio/install", response_model=DeepAudioInstallStatus)
async def install_deep_audio(background_tasks: BackgroundTasks):
    status = deep_audio_service.get_install_status()
    if status["status"] == "installing":
        raise HTTPException(status_code=409, detail="Installation already in progress")
    if status["status"] == "completed":
        return status
        
    # Check disk space (min 2.5 GB)
    import shutil
    total, used, free = shutil.disk_usage(str(deep_audio_service.CACHE_DIR.parent))
    if free < 2.5 * 1024**3:
        raise HTTPException(status_code=400, detail=f"Brak wymaganego miejsca na dysku. Wymagane 2.5 GB, dostępne {free / 1024**3:.2f} GB.")
        
    background_tasks.add_task(deep_audio_service.install_deep_audio_background)
    return {"status": "installing", "message": "Pobieranie i instalowanie modeli...", "error": None}

@app.get("/api/v1/deep-audio/install", response_model=DeepAudioInstallStatus)
async def get_install_deep_audio():
    return deep_audio_service.get_install_status()

@app.post("/api/v1/files/{file_id}/deep-audio")
async def trigger_deep_audio(file_id: int, background_tasks: BackgroundTasks):
    if file_id not in state.files_db:
        raise HTTPException(status_code=404, detail="File not found")
        
    status = deep_audio_service.get_install_status()
    if status["status"] != "completed":
        raise HTTPException(status_code=400, detail="Deep Audio Analysis module is not installed yet.")
        
    file_path = state.files_db[file_id].get("path")
    if not file_path:
        raise HTTPException(status_code=404, detail="Original file path missing")
        
    background_tasks.add_task(deep_audio_service.process_deep_audio_task, file_id, file_path)
    return {"success": True}

@app.get("/api/v1/files/{file_id}/deep-audio-data", response_model=DeepAudioStatusResponse)
async def get_deep_audio_data(file_id: int, response: Response):
    if file_id not in state.files_db:
        raise HTTPException(status_code=404, detail="File not found")
        
    analysis = state.files_db[file_id].get("deep_audio")
    if not analysis:
        response.status_code = 202
        return {"status": "processing"}
        
    if analysis["status"] == "processing":
        response.status_code = 202
        return {"status": "processing"}
    elif analysis["status"] == "failed":
        return {"status": "failed", "error": analysis["error"]}
    elif analysis["status"] == "completed":
        return {"status": "completed", "data": analysis["data"]}
    else:
        response.status_code = 202
        return {"status": "processing"}

@app.get("/api/v1/files/stream/{file_id}", response_class=FileResponse)
async def stream_file(request: Request, file_id: int):
    return video_service.get_file_stream(file_id)

@app.delete("/api/v1/files/{file_id}", response_model=DeleteFileResponse)
async def delete_file(file_id: int):
    return video_service.delete_file(file_id)


from parsers import parse_filename, ParserError



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
    return vision_service.process_analyze_elements(req)

@app.post("/api/v1/copydeck/parse", response_model=CopydeckParseResponse)
async def parse_copydeck(file: UploadFile = File(...)):
    return await process_copydeck_file(file)

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
            return HTMLResponse((frontend_dist / "index.html").read_text())
        
        target = frontend_dist / file_path
        if target.exists() and target.is_file():
            return FileResponse(target)
        
        # SPA fallback
        return HTMLResponse((frontend_dist / "index.html").read_text())
