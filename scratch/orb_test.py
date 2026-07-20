import cv2

template_path = "/Volumes/PL-EGplusww/Administrative and corporate files/DEPARTMENTS/QA/VITO/CV_Assets/BING/1x1/Universal/shot1.png"
template = cv2.imread(template_path, cv2.IMREAD_GRAYSCALE)
frame = cv2.imread("/tmp/test_frame_14s.png", cv2.IMREAD_GRAYSCALE)

orb = cv2.ORB_create()
kp1, des1 = orb.detectAndCompute(template, None)
kp2, des2 = orb.detectAndCompute(frame, None)

bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
matches = bf.match(des1, des2)
matches = sorted(matches, key=lambda x: x.distance)

good_matches = [m for m in matches if m.distance < 50]
print(f"ORB found {len(good_matches)} good matches")

sift = cv2.SIFT_create()
kp1_s, des1_s = sift.detectAndCompute(template, None)
kp2_s, des2_s = sift.detectAndCompute(frame, None)
bf_s = cv2.BFMatcher()
matches_s = bf_s.knnMatch(des1_s, des2_s, k=2)

good_sift = []
for m, n in matches_s:
    if m.distance < 0.75 * n.distance:
        good_sift.append(m)
print(f"SIFT found {len(good_sift)} good matches")
