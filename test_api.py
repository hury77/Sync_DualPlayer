import requests
import base64
import json
import cv2
import numpy as np

# Create a dummy image
img = np.zeros((400, 400, 3), dtype=np.uint8)
img[:] = (150, 0, 0)
_, buffer = cv2.imencode('.jpg', img)
b64_str = "data:image/jpeg;base64," + base64.b64encode(buffer).decode('utf-8')

payload = {
    "image_base64": b64_str,
    "country_code": "CA-FR"
}

try:
    response = requests.post("http://localhost:8003/api/v1/analyze-elements", json=payload)
    print("Status:", response.status_code)
    print("Response:", response.json())
except Exception as e:
    print("Error:", e)
