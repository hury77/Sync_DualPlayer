import cv2
import sys

video_path = "/Users/hubert.rycaj/Downloads/Playstation do testow/1017736/Guest-Pillars-Trailer_SE-SV_Video_1080x1080_15s-Cutdown_2997fps_FrontCTA_02.mp4"
template_path = "/Volumes/PL-EGplusww/Administrative and corporate files/DEPARTMENTS/QA/VITO/CV_Assets/BONG/1x1/Universal/shot1_cropped.png"

template = cv2.imread(template_path, cv2.IMREAD_UNCHANGED)
if template is None:
    print("Could not load template")
    sys.exit(1)

if len(template.shape) == 3 and template.shape[2] == 4:
    template = cv2.cvtColor(template, cv2.COLOR_BGRA2BGR)
else:
    template = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY) # wait, we should stick to BGR if it's 3-channel
    if len(template.shape) == 2:
        template = cv2.cvtColor(template, cv2.COLOR_GRAY2BGR)

# Reload template strictly as BGR to match main.py logic
template = cv2.imread(template_path, cv2.IMREAD_COLOR)

cap = cv2.VideoCapture(video_path)
total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
fps = cap.get(cv2.CAP_PROP_FPS)
start_frame = max(0, total_frames - int(fps * 5)) # Last 5 seconds

cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
max_score = 0
best_frame = start_frame

while True:
    ret, frame = cap.read()
    if not ret:
        break
    
    current_f = int(cap.get(cv2.CAP_PROP_POS_FRAMES))
    
    if template.shape[0] > frame.shape[0] or template.shape[1] > frame.shape[1]:
        continue
        
    res = cv2.matchTemplate(frame, template, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, _ = cv2.minMaxLoc(res)
    
    if max_val >= 0.7:
        print(f"Frame {current_f}: {max_val:.3f}")
        
    if 400 <= current_f <= 415:
        cv2.imwrite(f"/Users/hubert.rycaj/Documents/Sync_DualPlayer/scratch/frame_{current_f}.jpg", frame)
    
    if max_val > max_score:
        max_score = max_val
        best_frame = current_f

print(f"BONG: Best score {max_score:.3f} at frame {best_frame} (Total {total_frames})")
