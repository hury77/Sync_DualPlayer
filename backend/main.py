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
