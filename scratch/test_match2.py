import cv2
import numpy as np

img = np.zeros((270, 270, 3), dtype=np.uint8)
img[:] = (255, 255, 255) # White background

template = np.zeros((50, 50, 4), dtype=np.uint8)
template[10:40, 10:40] = (255, 0, 0, 255) # Blue square
mask = template[:, :, 3]
template_bgr = cv2.cvtColor(template, cv2.COLOR_BGRA2BGR)

res_mask = cv2.matchTemplate(img, template_bgr, cv2.TM_CCORR_NORMED, mask=mask)
_, max_val_mask, _, _ = cv2.minMaxLoc(res_mask)
print(f"Mismatch (blue template on white img) with mask: {max_val_mask}")
