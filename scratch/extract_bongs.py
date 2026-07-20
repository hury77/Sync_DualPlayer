import cv2
import sys
import os

def extract_last_frame(video_path, output_path):
    print(f"Extracting last frame from {video_path}")
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"Error opening video {video_path}")
        return
        
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    cap.set(cv2.CAP_PROP_POS_FRAMES, total_frames - 2)
    ret, frame = cap.read()
    
    if ret:
        cv2.imwrite(output_path, frame)
        print(f"Saved to {output_path}")
    else:
        print("Failed to read last frame")
        
    cap.release()

v1 = "/Users/hubert.rycaj/Documents/PS_elements/BONG/2.0s/EN_TM/29_97/SIE_BONG_2_1_EN_TM_20s_4K_2997f_V003.mov"
v2 = "/Users/hubert.rycaj/Documents/PS_elements/BONG/2.0s/EN_R/29_97/SIE_BONG_2_1_EN_R_20s_4K_2997f_V004.mov"
out1 = "/Users/hubert.rycaj/Documents/PS_elements/CV_Assets/BONG/16x9/Universal/shot1.png"
out2 = "/Users/hubert.rycaj/Documents/PS_elements/CV_Assets/BONG/16x9/Universal/shot2.png"

extract_last_frame(v1, out1)
extract_last_frame(v2, out2)
