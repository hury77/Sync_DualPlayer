import requests
import json

url = "http://127.0.0.1:8003/api/v1/analyze-elements"
frame_path = "/tmp/debug_frame_1782484077.png"

data = {
    "filename": "Guest-Pillars-Trailer_IT-IT_Video_1080x1080_30s-Cutdown_2997fps_FrontCTA_01.mp4",
    "timestamp": 29.5,
    "requirements": json.dumps({
        "BONG": "YES",
        "PHNL LOCK-UP LOCALISED?": "NO",
        "PHNL LANGUAGE": "ITALIAN"
    })
}

with open(frame_path, "rb") as f:
    files = {"frame": ("frame.png", f, "image/png")}
    response = requests.post(url, data=data, files=files)

print("Status Code:", response.status_code)
res_json = response.json()
print("BONG status:", res_json.get("bong"))
print("BING status:", res_json.get("bing"))
