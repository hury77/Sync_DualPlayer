import cv2
video_path = "/Users/hubert.rycaj/Documents/PS_elements/BONG/2.0s/EN_R/29_97/SIE_BONG_2_1_EN_R_20s_1X1_2997f_V004.mov"
cap = cv2.VideoCapture(video_path)
total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
print(f"Total frames: {total}")

cap.set(cv2.CAP_PROP_POS_FRAMES, 15)
ret1, frame15 = cap.read()
if ret1: cv2.imwrite("scratch/frame15.png", frame15)

cap.set(cv2.CAP_PROP_POS_FRAMES, 50)
ret2, frame50 = cap.read()
if ret2: cv2.imwrite("scratch/frame50.png", frame50)

# Check the difference
if ret1 and ret2:
    diff = cv2.absdiff(frame15, frame50)
    print(f"Mean diff between 15 and 50: {diff.mean()}")
