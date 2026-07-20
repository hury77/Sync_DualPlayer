import subprocess
import time
import requests
import json
import os

# Start server
proc = subprocess.Popen(["uvicorn", "main:app", "--host", "127.0.0.1", "--port", "8004"], 
                        cwd="/Users/hubert.rycaj/Documents/Sync_DualPlayer/backend",
                        stdout=subprocess.PIPE, stderr=subprocess.PIPE)
time.sleep(2) # wait for startup

url = "http://127.0.0.1:8004/api/v1/analyze-elements"
frame_path = "/tmp/debug_frame_1782484077.png"
data = {
    "filename": "Guest-Pillars-Trailer_IT-IT_Video_1080x1080_30s-Cutdown_2997fps_FrontCTA_01.mp4",
    "timestamp": 29.5,
    "requirements": json.dumps({"country": "IT", "rating": "PEGI 18", "bing": "PS Logo", "bong": "Standard"})
}

try:
    with open(frame_path, "rb") as f:
        files = {"frame": ("frame.png", f, "image/png")}
        resp = requests.post(url, data=data, files=files)
    print("Status:", resp.status_code)
except Exception as e:
    print("Request failed:", e)

proc.terminate()
stdout, stderr = proc.communicate()
print("SERVER STDERR:")
print(stderr.decode())
