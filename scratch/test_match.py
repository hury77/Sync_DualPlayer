import cv2
import numpy as np

# Create solid blue image 270x270
img = np.zeros((270, 270, 3), dtype=np.uint8)
img[:] = (255, 0, 0) # Blue in BGR

# Create template 50x50 with alpha
template = np.zeros((50, 50, 4), dtype=np.uint8)
template[10:40, 10:40] = (255, 255, 255, 255) # White square in center
# transparent border (alpha=0)

# Put template on image (composite)
img[100:150, 100:150] = (255, 255, 255) # Put the white square on blue background

# Now test matchTemplate WITHOUT alpha
template_bgr = cv2.cvtColor(template, cv2.COLOR_BGRA2BGR)
res = cv2.matchTemplate(img, template_bgr, cv2.TM_CCOEFF_NORMED)
_, max_val, _, _ = cv2.minMaxLoc(res)
print(f"Without mask: {max_val}")

# Now test matchTemplate WITH alpha mask using CCORR_NORMED
mask = template[:, :, 3]
res_mask = cv2.matchTemplate(img, template_bgr, cv2.TM_CCORR_NORMED, mask=mask)
_, max_val_mask, _, _ = cv2.minMaxLoc(res_mask)
print(f"With mask (CCORR_NORMED): {max_val_mask}")
