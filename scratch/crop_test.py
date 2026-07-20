import cv2
import numpy as np

template_path = "/Volumes/PL-EGplusww/Administrative and corporate files/DEPARTMENTS/QA/VITO/CV_Assets/BING/1x1/Universal/shot1.png"
template = cv2.imread(template_path, cv2.IMREAD_COLOR)

# Szukamy jasnych pikseli (białe logo)
gray = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
_, thresh = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY)

coords = cv2.findNonZero(thresh)
if coords is not None:
    x, y, w, h = cv2.boundingRect(coords)
    print(f"Found bounding box: x={x}, y={y}, w={w}, h={h}")
    cropped = template[y:y+h, x:x+w]
    cv2.imwrite("/tmp/cropped_template.png", cropped)
    
    # Test match na wideo:
    frame = cv2.imread("/tmp/test_frame_14s.png")
    res = cv2.matchTemplate(frame, cropped, cv2.TM_CCOEFF_NORMED)
    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
    print(f"Match Template (cropped): max_val = {max_val}")
else:
    print("Could not find white pixels")
