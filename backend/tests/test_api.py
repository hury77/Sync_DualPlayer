import pytest
import asyncio
from httpx import AsyncClient, ASGITransport
import os
from pathlib import Path

# Add parent path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from main import app

FIXTURES_DIR = Path(__file__).parent / "fixtures"
TEST_VIDEO = FIXTURES_DIR / "test_video.mp4"
TEST_BRIEF = FIXTURES_DIR / "test_brief.xlsx"
DUMMY_TXT = FIXTURES_DIR / "dummy_file.txt"
CV_ASSETS_MOCK = FIXTURES_DIR / "cv_assets_mock"

@pytest.mark.asyncio
async def test_upload_video_and_poll_status():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        with open(TEST_VIDEO, "rb") as f:
            response = await client.post(
                "/api/v1/files/upload",
                data={"file_type": "Acceptance"},
                files={"file": ("test_video.mp4", f, "video/mp4")}
            )
        assert response.status_code == 200
        data = response.json()
        assert "file_id" in data
        file_id = data["file_id"]
        
        # Poll status
        max_retries = 20
        status_data = None
        for _ in range(max_retries):
            status_resp = await client.get(f"/api/v1/files/{file_id}")
            assert status_resp.status_code == 200
            status_data = status_resp.json()
            if status_data["is_processed"] or status_data.get("processing_error"):
                break
            await asyncio.sleep(0.5)
        
        assert status_data is not None
        assert status_data["is_processed"] is True
        assert status_data["processing_error"] is None

@pytest.mark.asyncio
async def test_delete_file_success():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        with open(TEST_VIDEO, "rb") as f:
            upload_resp = await client.post(
                "/api/v1/files/upload",
                data={"file_type": "Emission"},
                files={"file": ("test_video.mp4", f, "video/mp4")}
            )
        file_id = upload_resp.json()["file_id"]
        
        for _ in range(10):
            status_resp = await client.get(f"/api/v1/files/{file_id}")
            if status_resp.json()["is_processed"]:
                break
            await asyncio.sleep(0.2)
            
        delete_resp = await client.delete(f"/api/v1/files/{file_id}")
        assert delete_resp.status_code == 200
        
        # Verify it's gone
        status_resp = await client.get(f"/api/v1/files/{file_id}")
        assert status_resp.status_code == 404

@pytest.mark.asyncio
async def test_delete_file_error(monkeypatch):
    """
    Test 3: Próba usunięcia pliku kończąca się błędem 500.
    Mockujemy os.remove aby rzucił wyjątek i zweryfikował komunikat dodany w etapie 1B.2.
    """
    def mock_remove(*args, **kwargs):
        raise PermissionError("Mock permission denied")
        
    monkeypatch.setattr(os, "remove", mock_remove)
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        with open(TEST_VIDEO, "rb") as f:
            upload_resp = await client.post(
                "/api/v1/files/upload",
                data={"file_type": "Acceptance"},
                files={"file": ("test_video.mp4", f, "video/mp4")}
            )
        file_id = upload_resp.json()["file_id"]
        
        for _ in range(10):
            if (await client.get(f"/api/v1/files/{file_id}")).json()["is_processed"]:
                break
            await asyncio.sleep(0.2)
            
        response = await client.delete(f"/api/v1/files/{file_id}")
        assert response.status_code == 500
        assert "Nie udało się usunąć" in response.json()["detail"]

@pytest.mark.asyncio
async def test_reject_invalid_brief_extensions():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        # Test 1: generic txt
        with open(DUMMY_TXT, "rb") as f:
            resp_txt = await client.post(
                "/api/v1/brief/upload",
                files={"file": ("dummy_file.txt", f, "text/plain")}
            )
        assert resp_txt.status_code == 422
        
        # Test 2: mp4 mistakenly uploaded as brief
        with open(TEST_VIDEO, "rb") as f:
            resp_mp4 = await client.post(
                "/api/v1/brief/upload",
                files={"file": ("test_video.mp4", f, "video/mp4")}
            )
        assert resp_mp4.status_code == 422

@pytest.mark.asyncio
async def test_upload_brief_with_mocked_cv_assets(monkeypatch):
    import config
    import brief_service
    import state
    from pathlib import Path
    
    # Mock the CV_Assets path to our fixture directory
    cv_mock_path = Path(CV_ASSETS_MOCK)
    monkeypatch.setattr(config.settings, "cv_assets_path", str(cv_mock_path))
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        with open(TEST_BRIEF, "rb") as f:
            response = await client.post(
                "/api/v1/brief/upload",
                files={"file": ("test_brief.xlsx", f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
            )
        assert response.status_code == 200
        
        # Test get_cached_brief_data logic which runs ORB matching
        brief_path = str(state.UPLOAD_DIR / "current_brief.xlsx")
        reqs, icon_bytes, best_db_path = brief_service.get_cached_brief_data(
            brief_path, "PL-PL", cv_mock_path
        )
        
        assert reqs.get("RATING") == "PEGI"
        assert reqs.get("AGE") == "18"
        assert icon_bytes is not None
        assert best_db_path is not None
        assert "18_cropped.png" in str(best_db_path)
