import cv2
import numpy as np
from pathlib import Path

cv_assets_dir = Path("/Users/hubert.rycaj/Documents/PS_elements/CV_Assets")
rating_org = "ESRB"
rating_age = "T"

rating_folder = cv_assets_dir / "RATINGS" / rating_org
rating_path = ""
if rating_folder.exists():
    for f in rating_folder.glob("*_cropped.png"):
        name_upper = f.name.upper()
        if "_T_" in name_upper or "TEEN_" in name_upper or "ESRB_T" in name_upper:
            print(f"Match: {f.name}")
