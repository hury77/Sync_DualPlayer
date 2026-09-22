import os
import sys
import asyncio
import subprocess
import shutil
import json
import time
import logging
import traceback
from pathlib import Path
from typing import Dict, Any, Optional
import imageio_ffmpeg

import state

logger = logging.getLogger(__name__)

CACHE_DIR = Path(__file__).parent / ".cache" / "audio_analysis"
CACHE_DIR.mkdir(parents=True, exist_ok=True)
FLAG_FILE = Path(__file__).parent / ".cache" / "deep_audio_installed.flag"
PERF_LOG_FILE = Path(__file__).parent / ".cache" / "deep_audio_performance_log.jsonl"

def get_install_status() -> Dict[str, Any]:
    with state.deep_audio_install_lock:
        if FLAG_FILE.exists():
            return {"status": "completed", "message": "Deep Audio is installed", "error": None}
        return state.deep_audio_install_status.copy()

async def install_deep_audio_background():
    with state.deep_audio_install_lock:
        state.deep_audio_install_status["status"] = "installing"
        state.deep_audio_install_status["message"] = "Downloading and installing dependencies..."
        state.deep_audio_install_status["error"] = None

    try:
        req_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "requirements_deep_audio.txt")
        if not os.path.exists(req_path):
            raise RuntimeError(f"requirements file not found: {req_path}")

        # Install using pip
        cmd = [sys.executable, "-m", "pip", "install", "-r", req_path]
        
        # Omijanie problemu z certyfikatami w tescie
        env = os.environ.copy()
        
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env
        )
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            raise RuntimeError(f"pip install failed with code {process.returncode}:\n{stderr.decode('utf-8', errors='ignore')}")

        # Testowy import by potwierdzić
        test_script = "import torch; import demucs; import faster_whisper; print('OK')"
        test_cmd = [sys.executable, "-c", test_script]
        test_process = await asyncio.create_subprocess_exec(
            *test_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env
        )
        test_out, test_err = await test_process.communicate()
        
        if test_process.returncode != 0:
            raise RuntimeError(f"Test import failed after pip install: {test_err.decode('utf-8', errors='ignore')}")

        # Zapisz flage sukcesu
        FLAG_FILE.touch()
        with state.deep_audio_install_lock:
            state.deep_audio_install_status["status"] = "completed"
            state.deep_audio_install_status["message"] = "Install successful"
            
    except Exception as e:
        logger.error(f"Deep Audio install failed: {e}")
        traceback.print_exc()
        
        # Czyszczenie i uninstall w razie bledu
        try:
            print("Executing rollback: cleaning up pip cache and partial packages...", flush=True)
            cleanup_cmd = [sys.executable, "-m", "pip", "uninstall", "-y", "torch", "torchaudio", "demucs", "faster-whisper", "torchvision"]
            res1 = subprocess.run(cleanup_cmd, check=False, capture_output=True, text=True)
            print(f"Rollback uninstall output: {res1.stdout}", flush=True)
            res2 = subprocess.run([sys.executable, "-m", "pip", "cache", "purge"], check=False, capture_output=True, text=True)
            print(f"Rollback cache purge output: {res2.stdout}", flush=True)
        except Exception as cleanup_err:
            print(f"Failed to cleanup after install error: {cleanup_err}", flush=True)
            
        with state.deep_audio_install_lock:
            state.deep_audio_install_status["status"] = "failed"
            state.deep_audio_install_status["error"] = str(e)


def extract_audio_duration(file_path: str) -> float:
    exe = imageio_ffmpeg.get_ffmpeg_exe()
    cmd = [exe, '-i', file_path]
    res = subprocess.run(cmd, capture_output=True, text=True)
    out = res.stderr
    
    import re
    match = re.search(r"Duration:\s*(\d+):(\d+):(\d+\.\d+)", out)
    if match:
        h, m, s = match.groups()
        return float(h)*3600 + float(m)*60 + float(s)
    return 0.0

def run_deep_audio_analysis_sync(file_path: str) -> Dict[str, Any]:
    duration = extract_audio_duration(file_path)
    if duration > 120.0:
        raise ValueError(f"Plik audio przekracza limit 120 sekund (trwa {duration:.1f}s). Analiza przerwana.")
        
    start_time = time.time()
    
    import torch
    from faster_whisper import WhisperModel
    import httpx
    
    import certifi
    os.environ["SSL_CERT_FILE"] = certifi.where()
    
    # 1. Transkrypcja Whisper base
    model = WhisperModel("base", device="cpu", compute_type="int8")
    segments, info = model.transcribe(file_path, beam_size=5)
    transcription = []
    for segment in segments:
        transcription.append({
            "start": segment.start,
            "end": segment.end,
            "text": segment.text
        })
        
    # Zwolnij pamiec po Whisper (okolo 750MB) przed ladowaniem Demucs (1.2GB)
    del model
    import gc
    gc.collect()
        
    # 2. Separacja Demucs using API
    import torch
    from demucs.pretrained import get_model
    from demucs.apply import apply_model
    from demucs.audio import AudioFile, save_audio
    
    demucs_out_dir = Path(__file__).parent / "separated" / "htdemucs" / Path(file_path).stem
    demucs_out_dir.mkdir(parents=True, exist_ok=True)
    
    
    
    model = get_model('htdemucs')
    model.cpu()
    model.eval()
    
    import torchaudio
    wav, sr = torchaudio.load(file_path)
    if sr != model.samplerate:
        wav = torchaudio.transforms.Resample(sr, model.samplerate)(wav)
    if wav.shape[0] == 1 and model.audio_channels == 2:
        wav = wav.repeat(2, 1)
    
    ref = wav.mean(0)
    wav = (wav - ref.mean()) / (ref.std() + 1e-8)
    wav = wav.clone() # Fix for RuntimeError: unsupported operation
    wav = wav[None]
    
    with torch.no_grad():
        sources = apply_model(model, wav, device="cpu", split=True, overlap=0.25)[0]
    sources = sources * ref.std() + ref.mean()
    
    # htdemucs outputs: drums, bass, other, vocals
    # Combine everything except vocals into 'no_vocals'
    vocals_idx = model.sources.index('vocals')
    vocals_source = sources[vocals_idx]
    
    other_sources = [s for i, s in enumerate(sources) if i != vocals_idx]
    no_vocals_source = sum(other_sources)
    
    save_audio(vocals_source, str(demucs_out_dir / "vocals.wav"), samplerate=model.samplerate)
    save_audio(no_vocals_source, str(demucs_out_dir / "no_vocals.wav"), samplerate=model.samplerate)
    processing_time = time.time() - start_time
    
    stem_files = {}
    if (demucs_out_dir / "vocals.wav").exists():
        stem_files["vocals"] = str(demucs_out_dir / "vocals.wav")
    if (demucs_out_dir / "no_vocals.wav").exists():
        stem_files["no_vocals"] = str(demucs_out_dir / "no_vocals.wav")
        
    # Log telemetry
    import resource
    maxrss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    # On macOS ru_maxrss is in bytes, on Linux in kilobytes
    import sys
    if sys.platform == "darwin":
        peak_ram_mb = maxrss / (1024 * 1024)
    else:
        peak_ram_mb = maxrss / 1024
        
    log_entry = {
        "timestamp": time.time(),
        "model_variant": "whisper_base+demucs_two_stems_vocals",
        "file_duration_seconds": duration,
        "processing_time_seconds": round(processing_time, 2),
        "peak_ram_mb": round(peak_ram_mb, 2)
    }
    
    with open(PERF_LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(log_entry) + "\n")
        
    return {
        "stems": stem_files,
        "transcription": transcription,
        "processing_time_seconds": round(processing_time, 2)
    }

_analysis_lock = asyncio.Lock()

async def process_deep_audio_task(file_id: int, file_path: str):
    if file_id not in state.files_db:
        return
        
    state.files_db[file_id]["deep_audio"] = {
        "status": "processing",
        "data": None,
        "error": None
    }
    
    try:
        loop = asyncio.get_running_loop()
        
        # 1. Oblicz sha256 za pomoca audio_service.calc_sha256
        import audio_service
        file_hash = await loop.run_in_executor(None, audio_service.calc_sha256, file_path)
        cache_file = CACHE_DIR / f"{file_hash}_deep.json"
        
        # 2. Sprawdz osobny cache
        if cache_file.exists():
            try:
                with open(cache_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if file_id in state.files_db:
                    state.files_db[file_id]["deep_audio"]["status"] = "completed"
                    state.files_db[file_id]["deep_audio"]["data"] = data
                return
            except Exception as e:
                logger.warning(f"Deep cache read error for {cache_file}: {e}")
                
        # 3. Analiza - ograniczona przez semafor/lock do 1 na raz
        async with _analysis_lock:
            result_data = await loop.run_in_executor(None, run_deep_audio_analysis_sync, file_path)
        
        # 4. Zapisz cache
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(result_data, f)
            
        if file_id in state.files_db:
            state.files_db[file_id]["deep_audio"]["status"] = "completed"
            state.files_db[file_id]["deep_audio"]["data"] = result_data
            
    except Exception as e:
        logger.error(f"Deep audio analysis failed for file_id {file_id}: {e}")
        traceback.print_exc()
        if file_id in state.files_db:
            state.files_db[file_id]["deep_audio"]["status"] = "failed"
            state.files_db[file_id]["deep_audio"]["error"] = str(e)

