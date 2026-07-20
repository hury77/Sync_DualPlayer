import cv2
import sys
sys.path.append("/Users/hubert.rycaj/Documents/Sync_DualPlayer/backend")
from main import match_template

template_path = "/Users/hubert.rycaj/Documents/PS_elements/CV_Assets/BONG/16x9/EN_R/shot1_cropped.png"
frame_path = "/tmp/debug_frame_1782484077.png"

img = cv2.imread(frame_path, cv2.IMREAD_COLOR)
res = match_template(img, template_path)
print(f"Match against 16x9 template: {res}")
