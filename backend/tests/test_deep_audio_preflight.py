import os
import pytest
import tempfile
import asyncio
from unittest.mock import patch
from backend.deep_audio_service import extract_audio_if_needed, state, process_deep_audio_task

def test_extract_audio_if_needed_mp4_success():
    # Setup test state for logging
    file_id = 901
    state.files_db[file_id] = {"file_path": "backend/real_video.mp4", "deep_audio": {}}
    
    audio_load_path, temp_wav_path = extract_audio_if_needed("backend/real_video.mp4", file_id)
    
    assert temp_wav_path is not None
    assert audio_load_path == temp_wav_path
    assert os.path.exists(temp_wav_path)
    
    # Verify file is a valid non-empty WAV
    assert os.path.getsize(temp_wav_path) > 1000
    
    # Cleanup manually since we called helper directly
    os.unlink(temp_wav_path)

def test_extract_audio_if_needed_wav_skips():
    file_id = 902
    state.files_db[file_id] = {"file_path": "backend/test_real.wav", "deep_audio": {}}
    
    audio_load_path, temp_wav_path = extract_audio_if_needed("backend/test_real.wav", file_id)
    
    assert temp_wav_path is None
    assert audio_load_path == "backend/test_real.wav"

def test_extract_audio_if_needed_mp4_noaudio_raises():
    file_id = 903
    state.files_db[file_id] = {"file_path": "noaudio.mp4", "deep_audio": {}}
    
    with pytest.raises(RuntimeError, match="Nie udało się przeanalizować pliku audio"):
        extract_audio_if_needed("noaudio.mp4", file_id)

@patch('subprocess.run')
def test_extract_audio_if_needed_timeout_raises(mock_run):
    import subprocess
    # Simulate a TimeoutExpired
    mock_run.side_effect = subprocess.TimeoutExpired(cmd="ffmpeg", timeout=120)
    
    file_id = 906
    state.files_db[file_id] = {"file_path": "backend/real_video.mp4", "deep_audio": {}}
    
    with pytest.raises(RuntimeError, match="Przekroczono czas oczekiwania na ekstrakcję audio"):
        extract_audio_if_needed("backend/real_video.mp4", file_id)

@pytest.mark.asyncio
@patch('faster_whisper.WhisperModel')
@patch('demucs.pretrained.get_model')
@patch('demucs.apply.apply_model')
@patch('demucs.audio.save_audio')
async def test_full_pipeline_cleanup_success(mock_save_audio, mock_apply, mock_get_model, mock_whisper):
    # Mock ML models to prevent heavy loading
    mock_model_instance = mock_whisper.return_value
    mock_model_instance.transcribe.return_value = ([], {})
    
    mock_demucs_model = mock_get_model.return_value
    mock_demucs_model.samplerate = 44100
    mock_demucs_model.audio_channels = 2
    mock_demucs_model.sources = ["vocals", "other"]
    
    import torch
    # apply_model returns a tuple, first element is a tensor
    mock_apply.return_value = (torch.zeros((2, 2, 44100)), )

    # We test process_deep_audio_task to ensure finally block executes
    file_id = 904
    file_path = "backend/real_video.mp4"
    state.files_db[file_id] = {"file_path": file_path, "deep_audio": {}}
    
    tempdir = tempfile.gettempdir()
    wavs_before = {f for f in os.listdir(tempdir) if f.endswith(".wav")}
    
    await process_deep_audio_task(file_id, file_path)
    
    wavs_after = {f for f in os.listdir(tempdir) if f.endswith(".wav")}
    leftovers = wavs_after - wavs_before
    
    assert len(leftovers) == 0, f"Leftover files found: {leftovers}"

@pytest.mark.asyncio
async def test_full_pipeline_cleanup_on_error():
    # Test error path (noaudio.mp4) and ensure cleanup runs
    file_id = 905
    file_path = "noaudio.mp4"
    state.files_db[file_id] = {"file_path": file_path, "deep_audio": {}}
    
    tempdir = tempfile.gettempdir()
    wavs_before = {f for f in os.listdir(tempdir) if f.endswith(".wav")}
    
    await process_deep_audio_task(file_id, file_path)
    
    wavs_after = {f for f in os.listdir(tempdir) if f.endswith(".wav")}
    leftovers = wavs_after - wavs_before
    
    assert len(leftovers) == 0, f"Leftover files found after error: {leftovers}"
    # Verify the state actually failed
    assert state.files_db[file_id]["deep_audio"]["status"] == "failed"
