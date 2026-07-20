import cv2
import numpy as np

video_path = "/Users/hubert.rycaj/Documents/PS_elements/BONG/2.0s/EN_R/29_97/SIE_BONG_2_1_EN_R_20s_1X1_2997f_V004.mov"
cap = cv2.VideoCapture(video_path)

for f_idx in range(5, 45, 5):
    cap.set(cv2.CAP_PROP_POS_FRAMES, f_idx)
    ret, frame = cap.read()
    if not ret: continue
    
    # Crop to text region
    H, W = frame.shape[:2]
    crop = frame[int(H*0.3):int(H*0.7), int(W*0.1):int(W*0.9)]
    
    # Calculate brightness of non-background pixels
    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    _, thresh = cv2.threshold(gray, 100, 255, cv2.THRESH_BINARY)
    text_pixels = np.sum(thresh == 255)
    
    print(f"Frame {f_idx}: {text_pixels} bright pixels")
