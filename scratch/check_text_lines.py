import cv2
import numpy as np

f15 = cv2.imread("scratch/bong_frame_15.png")
H, W = f15.shape[:2]
crop = f15[int(H*0.3):int(H*0.7), int(W*0.1):int(W*0.9)]
gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
_, thresh = cv2.threshold(gray, 100, 255, cv2.THRESH_BINARY)

# Find horizontal projection (sum across columns)
proj = np.sum(thresh == 255, axis=1)
lines = []
in_line = False
for i, p in enumerate(proj):
    if p > 0 and not in_line:
        in_line = True
        start = i
    elif p == 0 and in_line:
        in_line = False
        lines.append((start, i))
if in_line: lines.append((start, len(proj)))

print(f"Number of text lines: {len(lines)}")
for start, end in lines:
    print(f"Line from {start} to {end}, height {end-start}")
