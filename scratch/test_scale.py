import re

def get_base_scale(filename, image_w, bong_dim):
    # What was the original video width?
    dim_match = re.search(r'_(\d+)x(\d+)_', filename, re.IGNORECASE)
    if dim_match:
        orig_w = int(dim_match.group(1))
    elif "_4K_" in filename.upper():
        orig_w = 3840
    elif "_1080P_" in filename.upper():
        orig_w = 1920
    else:
        orig_w = 1920
        
    return image_w / orig_w

print(get_base_scale("Guest-Pillars-Trailer_IT-IT_Video_1080x1080_30s-Cutdown_2997fps_FrontCTA_01.mp4", 1080, "1x1"))
