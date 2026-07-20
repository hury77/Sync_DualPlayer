import cv2
import numpy as np

template_path = "/Volumes/PL-EGplusww/Administrative and corporate files/DEPARTMENTS/QA/VITO/CV_Assets/BING/1x1/Universal/shot1.png"
template = cv2.imread(template_path, cv2.IMREAD_COLOR)
frame = cv2.imread("/tmp/test_frame_14s.png")

# Binarize to find bounding box of logo in template
gray = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
_, thresh = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY)
coords = cv2.findNonZero(thresh)
x, y, w, h = cv2.boundingRect(coords)
cropped = template[y:y+h, x:x+w]
cropped_gray = cv2.cvtColor(cropped, cv2.COLOR_BGR2GRAY)

frame_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

found = None

# Loop over scales
for scale in np.linspace(0.5, 1.5, 20):
    new_w = int(cropped_gray.shape[1] * scale)
    new_h = int(cropped_gray.shape[0] * scale)
    if new_w == 0 or new_h == 0:
        continue
    resized = cv2.resize(cropped_gray, (new_w, new_h))
    if resized.shape[0] > frame_gray.shape[0] or resized.shape[1] > frame_gray.shape[1]:
        continue
        
    res = cv2.matchTemplate(frame_gray, resized, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, max_loc = cv2.minMaxLoc(res)
    
    if found is None or max_val > found[0]:
        found = (max_val, max_loc, scale)

print(f"Best Match: max_val={found[0]}, scale={found[2]}")
