from pathlib import Path
import threading

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

# In-memory database for standalone player
files_db = {}
file_counter = 1

_image_cache = {}
_image_cache_lock = threading.Lock()

_brief_cache = {}
_brief_cache_lock = threading.Lock()

deep_audio_install_status = {
    "status": "not_installed",
    "message": None,
    "error": None
}
deep_audio_install_lock = threading.Lock()
