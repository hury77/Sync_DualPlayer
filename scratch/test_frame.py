import cv2
import sys
import numpy as np
import os

video_path = "/Users/hubert.rycaj/Downloads/Playstation do testow/1017736/Guest-Pillars-Trailer_SE-SV_Video_1080x1080_15s-Cutdown_2997fps_FrontCTA_02.mp4"
template_path = "/Volumes/PL-EGplusww/Administrative and corporate files/DEPARTMENTS/QA/VITO/CV_Assets/BING/1x1/Universal/shot1.png"

cap = cv2.VideoCapture(video_path)
cap.set(cv2.CAP_PROP_POS_MSEC, 14000) # 14 seconds
ret, frame = cap.read()
if not ret:
    print("Could not read frame")
    sys.exit(1)

cv2.imwrite("/tmp/test_frame_14s.png", frame)
print("Saved /tmp/test_frame_14s.png")

template = cv2.imread(template_path, cv2.IMREAD_UNCHANGED)
if len(template.shape) == 3 and template.shape[2] == 4:
    template = cv2.cvtColor(template, cv2.COLOR_BGRA2BGR)

# OpenCV Match Template
res = cv2.matchTemplate(frame, template, cv2.TM_CCOEFF_NORMED)
min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)

print(f"Match Template (1080x1080 to 1080x1080): max_val = {max_val}")

