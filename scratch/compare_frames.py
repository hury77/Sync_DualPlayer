import cv2

f15 = cv2.imread("scratch/bong_frame_15.png")
f30 = cv2.imread("scratch/bong_frame_30.png")
f45 = cv2.imread("scratch/bong_frame_45.png")
f55 = cv2.imread("scratch/bong_frame_55.png")

print(f"Diff 15 vs 55: {cv2.absdiff(f15, f55).mean()}")
print(f"Diff 30 vs 55: {cv2.absdiff(f30, f55).mean()}")
print(f"Diff 45 vs 55: {cv2.absdiff(f45, f55).mean()}")
