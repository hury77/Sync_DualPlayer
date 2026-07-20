import cv2

f15 = cv2.imread("scratch/bong_frame_15.png")
# Check a pixel near the top left (should be background)
print(f"Top left pixel (B, G, R): {f15[10, 10]}")
