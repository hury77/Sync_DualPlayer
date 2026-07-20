import cv2
import numpy as np
from pathlib import Path

def get_template_orig_w(template_path: str) -> int:
    path_upper = template_path.upper()
    if "4K" in path_upper: return 3840
    elif "16X9" in path_upper:
        if "RATINGS" in path_upper: return 1920
        else: return 3840
    elif "1X1" in path_upper or "1:1" in path_upper: return 1080
    elif "9X16" in path_upper or "9:16" in path_upper: return 1080
    else: return 1920

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
        
    small_image = cv2.resize(image_np, (0, 0), fx=0.25, fy=0.25)
    small_template = cv2.resize(template, (0, 0), fx=0.25, fy=0.25, interpolation=cv2.INTER_AREA)
    if has_alpha:
        small_mask = cv2.resize(template_mask, (0, 0), fx=0.25, fy=0.25, interpolation=cv2.INTER_AREA)
    
    template_orig_w = get_template_orig_w(str(template_path))
    frontend_w = image_np.shape[1]
    exact_scale = frontend_w / template_orig_w
    print(f"exact_scale={exact_scale}, template_orig_w={template_orig_w}, frontend_w={frontend_w}")
    
    best_max_val = 0
    scales_to_check = [exact_scale * 0.95, exact_scale, exact_scale * 1.05]
    
    for scale in scales_to_check: 
        width = int(small_template.shape[1] * scale)
        height = int(small_template.shape[0] * scale)
        
        if width < 10 or height < 10 or width > small_image.shape[1] or height > small_image.shape[0]:
            print(f"Skipping scale {scale} because {width}x{height} > {small_image.shape[1]}x{small_image.shape[0]}")
            continue
            
        resized_template = cv2.resize(small_template, (width, height), interpolation=cv2.INTER_AREA)
        
        if has_alpha:
            resized_mask = cv2.resize(small_mask, (width, height), interpolation=cv2.INTER_AREA)
            res = cv2.matchTemplate(small_image, resized_template, cv2.TM_CCORR_NORMED, mask=resized_mask)
        else:
            res = cv2.matchTemplate(small_image, resized_template, cv2.TM_CCOEFF_NORMED)
            
        _, max_val, _, _ = cv2.minMaxLoc(res)
        print(f"Scale {scale} max_val: {max_val}")
        if max_val > best_max_val:
            best_max_val = max_val
            
    if best_max_val >= threshold:
        return True
    return False

cv_assets = "/Users/hubert.rycaj/Documents/PS_elements/CV_Assets"
bing_path = f"{cv_assets}/BING/1x1/Universal/shot1.png"
bing_img = cv2.imread(bing_path, cv2.IMREAD_COLOR)

print("Testing BING:")
print(match_template(bing_img, bing_path))

bong_uncropped_path = f"{cv_assets}/BONG/1x1/EN_R/shot1.png"
bong_path = f"{cv_assets}/BONG/1x1/EN_R/shot1_cropped.png"
bong_img = cv2.imread(bong_uncropped_path, cv2.IMREAD_COLOR)

print("Testing BONG:")
print(match_template(bong_img, bong_path))
