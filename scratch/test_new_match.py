import cv2
import os
import glob
from pathlib import Path

def test_template(image_path, template_path, title):
    if not os.path.exists(template_path):
        print(f"[{title}] Template missing: {template_path}")
        return
        
    image = cv2.imread(image_path)
    template = cv2.imread(template_path, cv2.IMREAD_UNCHANGED)
    if template is None: return
        
    if len(template.shape) == 3 and template.shape[2] == 4:
        template = cv2.cvtColor(template, cv2.COLOR_BGRA2BGR)
        
    small_image = cv2.resize(image, (0, 0), fx=0.25, fy=0.25)
    best_max_val = 0
    best_scale = 0
    import numpy as np
    for scale in np.linspace(0.1, 1.5, 29): # 29 scales from 0.1 to 1.5
        width = int(template.shape[1] * scale * 0.25)
        height = int(template.shape[0] * scale * 0.25)
        # print(f"  Scale {scale} -> width {width} height {height}")
        if width < 10 or height < 10 or width > small_image.shape[1] or height > small_image.shape[0]:
            continue
        resized_template = cv2.resize(template, (width, height), interpolation=cv2.INTER_AREA)
        res = cv2.matchTemplate(small_image, resized_template, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, _ = cv2.minMaxLoc(res)
        if max_val > best_max_val:
            best_max_val = max_val
            best_scale = scale
            
    print(f"[{title}] Best match in {os.path.basename(image_path)} -> Match: {best_max_val:.3f} at scale {best_scale:.2f}")

cv_dir = Path("/Users/hubert.rycaj/Documents/PS_elements/CV_Assets")
bing_template = cv_dir / "BING/16x9/Universal/shot1.png"
bong_en_r = cv_dir / "BONG/16x9/EN_R/shot1.png"
bong_en_tm = cv_dir / "BONG/16x9/EN_TM/shot1.png"

frames = sorted(glob.glob("/tmp/debug_frame_*.png"))
# Only test the last 30 frames to avoid clutter
for f in frames[-30:]:
    test_template(f, str(bing_template), "BING")
    test_template(f, str(bong_en_r), "BONG_EN_R")
    test_template(f, str(bong_en_tm), "BONG_EN_TM")
