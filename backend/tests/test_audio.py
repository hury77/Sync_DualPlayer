import pytest
import asyncio
from httpx import AsyncClient, ASGITransport
from pathlib import Path
import sys
import shutil

sys.path.insert(0, str(Path(__file__).parent.parent))
from main import app
from audio_service import CACHE_DIR

FIXTURES_DIR = Path(__file__).parent / "fixtures"
TEST_WAV = FIXTURES_DIR / "test_audio.wav"
TEST_CORRUPT = FIXTURES_DIR / "test_corrupt.wav"
TEST_VIDEO = FIXTURES_DIR / "test_video.mp4"

@pytest.fixture(autouse=True)
def clean_cache():
    if CACHE_DIR.exists():
        shutil.rmtree(CACHE_DIR)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    yield
    if CACHE_DIR.exists():
        shutil.rmtree(CACHE_DIR)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)

@pytest.mark.asyncio
async def test_upload_wav_and_poll_audio_data():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        with open(TEST_WAV, "rb") as f:
            resp = await client.post(
                "/api/v1/files/upload",
                data={"file_type": "Acceptance"},
                files={"file": ("test_audio.wav", f, "audio/wav")}
            )
        assert resp.status_code == 200
        file_id = resp.json()["file_id"]

        # Poll status
        max_retries = 20
        status_data = None
        for _ in range(max_retries):
            audio_resp = await client.get(f"/api/v1/files/{file_id}/audio-data")
            assert audio_resp.status_code == 200
            status_data = audio_resp.json()
            if status_data["status"] in ["completed", "failed"]:
                break
            await asyncio.sleep(0.5)

        assert status_data is not None
        assert status_data["status"] == "completed"
        
        data = status_data["data"]
        assert "metrics" in data
        assert data["metrics"]["lufs"] is not None
        assert data["metrics"]["peak"] is not None
        
        waveform = data["waveform"]
        assert len(waveform) > 0
        # Not all zeros
        assert any(x != 0 for x in waveform)
        # Not uniform (has dynamic variation)
        assert len(set(waveform)) > 1

@pytest.mark.asyncio
async def test_upload_wav_and_mp4_concurrently():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        with open(TEST_WAV, "rb") as f_wav:
            resp_wav = await client.post(
                "/api/v1/files/upload",
                data={"file_type": "Acceptance"},
                files={"file": ("test_audio.wav", f_wav, "audio/wav")}
            )
        assert resp_wav.status_code == 200
        file_id_wav = resp_wav.json()["file_id"]

        with open(TEST_VIDEO, "rb") as f_mp4:
            resp_mp4 = await client.post(
                "/api/v1/files/upload",
                data={"file_type": "Emission"},
                files={"file": ("test_video.mp4", f_mp4, "video/mp4")}
            )
        assert resp_mp4.status_code == 200
        file_id_mp4 = resp_mp4.json()["file_id"]
        
        # Poll both
        async def wait_for(fid):
            for _ in range(20):
                r = await client.get(f"/api/v1/files/{fid}/audio-data")
                status = r.json()["status"]
                if status in ["completed", "failed"]:
                    return status
                await asyncio.sleep(0.5)
            return "timeout"
            
        res_wav, res_mp4 = await asyncio.gather(wait_for(file_id_wav), wait_for(file_id_mp4))
        assert res_wav == "completed"
        # mp4 fixture lacks audio track, so it fails audio processing
        assert res_mp4 in ["completed", "failed"]

@pytest.mark.asyncio
async def test_upload_corrupt_file():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        with open(TEST_CORRUPT, "rb") as f:
            resp = await client.post(
                "/api/v1/files/upload",
                data={"file_type": "Acceptance"},
                files={"file": ("test_corrupt.wav", f, "audio/wav")}
            )
        assert resp.status_code == 200
        file_id = resp.json()["file_id"]

        max_retries = 20
        status_data = None
        for _ in range(max_retries):
            audio_resp = await client.get(f"/api/v1/files/{file_id}/audio-data")
            status_data = audio_resp.json()
            if status_data["status"] in ["completed", "failed"]:
                break
            await asyncio.sleep(0.5)

        assert status_data["status"] == "failed"
        assert "Nie udało się" in status_data["error"]

@pytest.mark.asyncio
async def test_audio_cache_hit():
    import time
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        # Upload 1
        with open(TEST_WAV, "rb") as f:
            resp1 = await client.post(
                "/api/v1/files/upload",
                data={"file_type": "Acceptance"},
                files={"file": ("test_audio1.wav", f, "audio/wav")}
            )
        file_id1 = resp1.json()["file_id"]
        
        # Wait for finish
        for _ in range(20):
            r = await client.get(f"/api/v1/files/{file_id1}/audio-data")
            if r.json()["status"] == "completed":
                break
            await asyncio.sleep(0.5)

        # Upload 2 (same file content, different name)
        t0 = time.time()
        with open(TEST_WAV, "rb") as f:
            resp2 = await client.post(
                "/api/v1/files/upload",
                data={"file_type": "Emission"},
                files={"file": ("test_audio2_copy.wav", f, "audio/wav")}
            )
        file_id2 = resp2.json()["file_id"]
        
        # Should be almost instantaneous due to cache
        for _ in range(20):
            r2 = await client.get(f"/api/v1/files/{file_id2}/audio-data")
            if r2.json()["status"] == "completed":
                break
            await asyncio.sleep(0.1)
            
        t1 = time.time()
        assert r2.json()["status"] == "completed"
        # The processing usually takes >1s (ffmpeg), cache should be <1s
        assert (t1 - t0) < 1.0
        
        # Data should match exactly
        assert r.json()["data"] == r2.json()["data"]

@pytest.mark.asyncio
async def test_silent_audio_inf_handling():
    # Testuje czy calkowicie cichy plik (-inf lufs) nie wywala endpointu
    TEST_SILENT = FIXTURES_DIR / "silent.wav"
    # Ensure the fixture exists
    if not TEST_SILENT.exists():
        pytest.skip("silent.wav fixture missing")
        
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        with open(TEST_SILENT, "rb") as f:
            resp = await client.post(
                "/api/v1/files/upload",
                data={"file_type": "Acceptance"},
                files={"file": ("silent.wav", f, "audio/wav")}
            )
        assert resp.status_code == 200
        file_id = resp.json()["file_id"]
        
        max_retries = 20
        status_data = None
        for _ in range(max_retries):
            audio_resp = await client.get(f"/api/v1/files/{file_id}/audio-data")
            status_data = audio_resp.json()
            if status_data["status"] in ["completed", "failed"]:
                break
            await asyncio.sleep(0.5)
            
        assert status_data["status"] == "completed"
        
        data = status_data["data"]
        # Sprawdz czy -inf zostalo prawidlowo odciete do -70.0/-99.0
        assert data["metrics"]["lufs"] == -70.0
        assert data["metrics"]["peak"] == -99.0

@pytest.mark.asyncio
async def test_vad_filters_silence_and_keeps_speech():
    from faster_whisper import WhisperModel
    audio_file = FIXTURES_DIR / "mixed_audio.wav"
    if not audio_file.exists():
        pytest.skip("mixed_audio.wav fixture missing")
        
    model = WhisperModel("tiny", compute_type="int8")
    
    # Bez VAD (powinno zacząć łapać halucynacje od 0.0s)
    segs_no_vad, _ = model.transcribe(str(audio_file), vad_filter=False)
    no_vad_list = list(segs_no_vad)
    
    # Z VAD (powinno zacząć się tam gdzie faktyczna mowa, np. ~2.6s)
    segs_vad, _ = model.transcribe(str(audio_file), vad_filter=True, vad_parameters=dict(min_silence_duration_ms=500))
    vad_list = list(segs_vad)
    
    assert len(no_vad_list) > 0, "No VAD should find some text"
    assert len(vad_list) > 0, "VAD should keep actual speech"
    assert vad_list[0].start > no_vad_list[0].start, "VAD should shift the start time after trimming silence"
