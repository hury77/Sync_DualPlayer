import pytest
import shutil
from pathlib import Path
import os
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
import state

@pytest.fixture(autouse=True)
def reset_state():
    """Reset the global state before each test."""
    state.files_db.clear()
    state.file_counter = 1
    with state._image_cache_lock:
        state._image_cache.clear()
    with state._brief_cache_lock:
        state._brief_cache.clear()
    
    if state.UPLOAD_DIR.exists():
        shutil.rmtree(state.UPLOAD_DIR)
    state.UPLOAD_DIR.mkdir(exist_ok=True)
    
    yield
