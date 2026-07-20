import cv2
import numpy as np

template_path = "/Volumes/PL-EGplusww/Administrative and corporate files/DEPARTMENTS/QA/VITO/CV_Assets/BING/1x1/Universal/shot1.png"
template = cv2.imread(template_path, cv2.IMREAD_COLOR)

frame = cv2.imread("/tmp/test_frame_14s.png")

# Convert both to grayscale
gray_temp = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

# Threshold both to get just the white logo (logo is white, background is blue/dark)
# We can use a high threshold to isolate white pixels
_, thresh_temp = cv2.threshold(gray_temp, 220, 255, cv2.THRESH_BINARY)
_, thresh_frame = cv2.threshold(gray_frame, 220, 255, cv2.THRESH_BINARY)

# Find bounding box in template
coords = cv2.findNonZero(thresh_temp)
if coords is not None:
    x, y, w, h = cv2.boundingRect(coords)
    # Crop the template to just the logo
    cropped_thresh_temp = thresh_temp[y:y+h, x:x+w]
    
    res = cv2.matchTemplate(thresh_frame, cropped_thresh_temp, cv2.TM_CCOEFF_NORMED)
    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
    print(f"Match Template (binarized & cropped): max_val = {max_val}")
else:
    print("No white pixels found in template")
