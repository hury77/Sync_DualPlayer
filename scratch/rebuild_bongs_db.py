import cv2
import os
import glob
from pathlib import Path

def extract_last_frame(video_path: str, output_path: str):
    print(f"Extracting {video_path} -> {output_path}")
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"Error opening video {video_path}")
        return
        
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    # BONG localized text is fully settled around frame 10
    cap.set(cv2.CAP_PROP_POS_FRAMES, 10)
    ret, frame = cap.read()
    
    if ret:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        cv2.imwrite(output_path, frame)
        
        # Crop center portion (PLAY HAS NO LIMITS text) to avoid legal text at the bottom
        H, W = frame.shape[:2]
        y1 = int(H * 0.3)
        y2 = int(H * 0.7)
        x1 = int(W * 0.1)
        x2 = int(W * 0.9)
        crop = frame[y1:y2, x1:x2]
        
        cropped_path = output_path.replace("shot1.png", "shot1_cropped.png")
        cv2.imwrite(cropped_path, crop)
    else:
        print("Failed to read last frame")
        
    cap.release()

source_dir = Path("/Users/hubert.rycaj/Documents/PS_elements/BONG/2.0s")
dest_dir = Path("/Users/hubert.rycaj/Documents/PS_elements/CV_Assets/BONG")

if not source_dir.exists():
    print(f"Source dir {source_dir} not found!")
    exit(1)

for lang_dir in source_dir.iterdir():
    if not lang_dir.is_dir(): continue
    lang = lang_dir.name
    mov_dir = lang_dir / "29_97"
    if not mov_dir.exists(): continue
    
    # Check 4K (16x9)
    mov_4k = list(mov_dir.glob("*_4K_*.mov"))
    if not mov_4k:
        mov_4k = list(mov_dir.glob("*_16X9_*.mov"))
    if mov_4k:
        out_path = dest_dir / "16x9" / lang / "shot1.png"
        extract_last_frame(str(mov_4k[0]), str(out_path))
        
    # Check 1x1
    mov_1x1 = list(mov_dir.glob("*_1X1_*.mov"))
    if mov_1x1:
        out_path = dest_dir / "1x1" / lang / "shot1.png"
        extract_last_frame(str(mov_1x1[0]), str(out_path))
        
    # Check 9x16
    mov_9x16 = list(mov_dir.glob("*_9X16_*.mov"))
    if mov_9x16:
        out_path = dest_dir / "9x16" / lang / "shot1.png"
        extract_last_frame(str(mov_9x16[0]), str(out_path))

print("Rebuilding complete.")
