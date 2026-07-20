import cv2
import glob
import os
import sys

# Get the latest 14 debug frames from /tmp
frames = sorted(glob.glob("/tmp/debug_frame_*.png"), key=os.path.getmtime)[-14:]
print(f"Testing on {len(frames)} latest debug frames from /tmp...")

template_path = "/Users/hubert.rycaj/Documents/PS_elements/CV_Assets/BONG/1x1/EN_R/shot1_cropped.png"

# Import our match_template from main.py
sys.path.append("/Users/hubert.rycaj/Documents/Sync_DualPlayer/backend")
from main import match_template

passed = False
for i, f in enumerate(frames):
    img = cv2.imread(f, cv2.IMREAD_COLOR)
    res = match_template(img, template_path)
    print(f"Frame {i} ({os.path.basename(f)}): {res}")
    if res: passed = True

print(f"Overall BONG match: {passed}")
