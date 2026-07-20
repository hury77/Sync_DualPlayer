import cv2

video_path = "/Users/hubert.rycaj/Documents/PS_elements/BONG/2.0s/EN_R/29_97/SIE_BONG_2_1_EN_R_20s_1X1_2997f_V004.mov"
cap = cv2.VideoCapture(video_path)

for f_idx in [5, 15, 30, 45, 55]:
    cap.set(cv2.CAP_PROP_POS_FRAMES, f_idx)
    ret, frame = cap.read()
    if ret:
        cv2.imwrite(f"scratch/bong_frame_{f_idx}.png", frame)
