import cv2
import numpy as np
from pathlib import Path

def match_template(image_np, template_path, threshold=0.7):
    template = cv2.imread(str(template_path), cv2.IMREAD_UNCHANGED)
    has_alpha = False
    if len(template.shape) == 3 and template.shape[2] == 4:
        has_alpha = True
        template_mask = template[:, :, 3]
        template = cv2.cvtColor(template, cv2.COLOR_BGRA2BGR)
        threshold = max(threshold, 0.75)
    else:
        template_mask = None
        
    tiny_img = cv2.resize(image_np, (0, 0), fx=0.125, fy=0.125)
    tiny_template = cv2.resize(template, (0, 0), fx=0.125, fy=0.125, interpolation=cv2.INTER_AREA)
    if has_alpha:
        tiny_mask = cv2.resize(template_mask, (0, 0), fx=0.125, fy=0.125, interpolation=cv2.INTER_AREA)
        
    best_scale_rough = 1.0
    best_val_rough = 0
    
    for scale in np.linspace(0.2, 1.5, 14):
        w = int(tiny_template.shape[1] * scale)
        h = int(tiny_template.shape[0] * scale)
        if w < 5 or h < 5 or w > tiny_img.shape[1] or h > tiny_img.shape[0]: continue
        
        rt = cv2.resize(tiny_template, (w, h), interpolation=cv2.INTER_AREA)
        if has_alpha:
            rm = cv2.resize(tiny_mask, (w, h), interpolation=cv2.INTER_AREA)
            res = cv2.matchTemplate(tiny_img, rt, cv2.TM_CCORR_NORMED, mask=rm)
        else:
            res = cv2.matchTemplate(tiny_img, rt, cv2.TM_CCOEFF_NORMED)
            
        _, max_val, _, _ = cv2.minMaxLoc(res)
        if max_val > best_val_rough:
            best_val_rough = max_val
            best_scale_rough = scale
            
    print(f"Best scale rough: {best_scale_rough} (val: {best_val_rough})")
            
    small_image = cv2.resize(image_np, (0, 0), fx=0.25, fy=0.25)
    small_template = cv2.resize(template, (0, 0), fx=0.25, fy=0.25, interpolation=cv2.INTER_AREA)
    if has_alpha:
        small_mask = cv2.resize(template_mask, (0, 0), fx=0.25, fy=0.25, interpolation=cv2.INTER_AREA)
        
    best_max_val = 0
    scales_to_check = [best_scale_rough * 0.9, best_scale_rough * 0.95, best_scale_rough, best_scale_rough * 1.05, best_scale_rough * 1.1]
    
    for scale in scales_to_check:
        w = int(small_template.shape[1] * scale)
        h = int(small_template.shape[0] * scale)
        if w < 10 or h < 10 or w > small_image.shape[1] or h > small_image.shape[0]: continue
        
        rt = cv2.resize(small_template, (w, h), interpolation=cv2.INTER_AREA)
        if has_alpha:
            rm = cv2.resize(small_mask, (w, h), interpolation=cv2.INTER_AREA)
            res = cv2.matchTemplate(small_image, rt, cv2.TM_CCORR_NORMED, mask=rm)
        else:
            res = cv2.matchTemplate(small_image, rt, cv2.TM_CCOEFF_NORMED)
            
        _, max_val, _, _ = cv2.minMaxLoc(res)
        print(f"Fine pass scale {scale}: {max_val}")
        if max_val > best_max_val:
            best_max_val = max_val
            
    return best_max_val >= threshold

cv_assets = "/Users/hubert.rycaj/Documents/PS_elements/CV_Assets"
bong_img = cv2.imread(f"{cv_assets}/BONG/1x1/EN_R/shot1.png", cv2.IMREAD_COLOR)
bong_path = f"{cv_assets}/BONG/1x1/EN_R/shot1_cropped.png"

print("Testing BONG with two-pass algorithm from main.py...")
res = match_template(bong_img, bong_path)
print(f"Result: {res}")
