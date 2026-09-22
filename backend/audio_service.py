import asyncio
import hashlib
import os
import subprocess
import json
import logging
import traceback
from pathlib import Path
from typing import Dict, Any, List, Optional
import numpy as np
import imageio_ffmpeg
import state

logger = logging.getLogger(__name__)

CACHE_DIR = Path(__file__).parent / ".cache" / "audio_analysis"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# Semafor ograniczający współbieżność do maksymalnie 2 równoległych analiz,
# by zapobiec przeciążeniu CPU przez ebur128 w przypadku masowego uploadu.
MAX_CONCURRENT_ANALYSES = 2
analysis_semaphore = asyncio.Semaphore(MAX_CONCURRENT_ANALYSES)

def calc_sha256(file_path: str) -> str:
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(65536), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def extract_ebur128(file_path: str):
    exe = imageio_ffmpeg.get_ffmpeg_exe()
    cmd = [exe, '-nostats', '-i', file_path, '-filter_complex', 'ebur128=peak=true', '-f', 'null', '-']
    res = subprocess.run(cmd, capture_output=True, text=True)
    
    if res.returncode != 0:
        raise RuntimeError(f"FFmpeg ebur128 error: {res.stderr}")
    
    lufs = None
    peak = None
    for line in res.stderr.split('\n'):
        if line.strip().startswith('I:'):
            try:
                lufs = float(line.split()[1])
            except ValueError:
                pass
        elif line.strip().startswith('Peak:'):
            try:
                peak = float(line.split()[1])
            except ValueError:
                pass
                
    if lufs is None or peak is None:
        raise RuntimeError("Could not parse LUFS or Peak from FFmpeg output")
        
    import math
    if math.isinf(peak) and peak < 0:
        peak = -99.0
    if math.isinf(lufs) and lufs < 0:
        lufs = -70.0
        
    return lufs, peak

def extract_waveform(file_path: str) -> List[float]:
    exe = imageio_ffmpeg.get_ffmpeg_exe()
    cmd = [exe, '-nostats', '-i', file_path, '-ac', '1', '-ar', '8000', '-f', 's16le', '-']
    res = subprocess.run(cmd, capture_output=True)
    
    if res.returncode != 0 and len(res.stdout) == 0:
        raise RuntimeError("FFmpeg waveform extraction failed, no output.")
        
    audio = np.frombuffer(res.stdout, dtype=np.int16)
    
    num_points = 1000
    if len(audio) == 0:
        return []
    
    chunk_size = len(audio) // num_points
    if chunk_size == 0:
        chunk_size = 1
        
    waveform = []
    for i in range(num_points):
        chunk = audio[i*chunk_size:(i+1)*chunk_size]
        if len(chunk) > 0:
            val = float(np.max(np.abs(chunk))) / 32768.0
            waveform.append(round(val, 4))
    
    return waveform

async def process_audio_analysis_task(file_id: int, file_path: str):
    """
    Background task uruchamiany z video_service przy uploadzie.
    Aktualizuje dict: state.files_db[file_id]["audio_analysis"]
    """
    if file_id not in state.files_db:
        return
        
    state.files_db[file_id]["audio_analysis"] = {
        "status": "processing",
        "data": None,
        "error": None
    }
    
    try:
        async with analysis_semaphore:
            loop = asyncio.get_running_loop()
            
            # 1. Oblicz sha256
            file_hash = await loop.run_in_executor(None, calc_sha256, file_path)
            cache_file = CACHE_DIR / f"{file_hash}.json"
            
            # 2. Sprawdź cache
            if cache_file.exists():
                try:
                    with open(cache_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    if file_id in state.files_db:
                        state.files_db[file_id]["audio_analysis"]["status"] = "completed"
                        state.files_db[file_id]["audio_analysis"]["data"] = data
                    return
                except Exception as e:
                    logger.warning(f"Cache read error for {cache_file}: {e}")
                    # fallback do ponownego wyliczenia
            
            # 3. Wylicz ebur128 i waveform
            lufs, peak = await loop.run_in_executor(None, extract_ebur128, file_path)
            waveform = await loop.run_in_executor(None, extract_waveform, file_path)
            
            result_data = {
                "metrics": {
                    "lufs": lufs,
                    "peak": peak,
                    "rms": None  # Placeholder, do wdrożenia, np z astats lub numpy
                },
                "waveform": waveform
            }
            
            # 4. Zapisz do cache
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(result_data, f)
                
            if file_id in state.files_db:
                state.files_db[file_id]["audio_analysis"]["status"] = "completed"
                state.files_db[file_id]["audio_analysis"]["data"] = result_data

    except Exception as e:
        logger.error(f"Audio analysis failed for file_id {file_id}: {e}")
        traceback.print_exc()
        if file_id in state.files_db:
            state.files_db[file_id]["audio_analysis"]["status"] = "failed"
            # Zwracamy przyjazny komunikat o błędzie (techniczny idzie do logów)
            if "Could not parse LUFS" in str(e) or "waveform extraction failed" in str(e) or "ebur128 error" in str(e):
                err_msg = "Nie udało się wyodrębnić ścieżki audio (brak audio lub nieobsługiwany format)."
            else:
                err_msg = "Wystąpił nieoczekiwany błąd podczas analizy dźwięku."
            state.files_db[file_id]["audio_analysis"]["error"] = err_msg
