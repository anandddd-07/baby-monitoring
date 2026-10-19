import sys
import time
from datetime import datetime

import cv2
import pandas as pd
import mediapipe as mp

print("Script started")

# Usage: python collect_eye.py Eyes_Open   OR   python collect_eye.py Eyes_Closed
name = sys.argv[1]
TOTAL = 900   # frames with a detected face

LEFT = [362, 385, 387, 263, 373, 380]
RIGHT = [33, 160, 158, 133, 153, 144]


def dist(a, b):
    return ((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2) ** 0.5


def get_ear(lms, idxs, w, h):
    pts = [(int(lms[i].x * w), int(lms[i].y * h)) for i in idxs]
    return (dist(pts[1], pts[5]) + dist(pts[2], pts[4])) / (2.0 * dist(pts[0], pts[3]))


face_mesh = mp.solutions.face_mesh.FaceMesh(
    max_num_faces=1, refine_landmarks=True,
    min_detection_confidence=0.5, min_tracking_confidence=0.5)

cap = cv2.VideoCapture(0)
rows = []

start = time.time()
while time.time() - start < 5:
    ret, frame = cap.read()
    if not ret:
        print("Camera not working")
        break
    frame = cv2.flip(frame, 1)
    left = int(5 - (time.time() - start)) + 1
    cv2.putText(frame, f"Get ready: {left}", (30, 60),
                cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 0, 255), 3)
    cv2.imshow("Collect eyes", frame)
    cv2.waitKey(1)

while len(rows) < TOTAL:
    ret, frame = cap.read()
    if not ret:
        break
    frame = cv2.flip(frame, 1)
    h, w, _ = frame.shape
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = face_mesh.process(rgb)

    if results.multi_face_landmarks:
        lms = results.multi_face_landmarks[0].landmark
        try:
            ear = (get_ear(lms, LEFT, w, h) + get_ear(lms, RIGHT, w, h)) / 2.0
            rows.append(ear)
            cv2.putText(frame, f"EAR: {ear:.2f}", (30, 80),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        except ZeroDivisionError:
            pass
    else:
        cv2.putText(frame, "No face found", (30, 80),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

    cv2.putText(frame, f"{name}: {len(rows)}/{TOTAL}", (30, 40),
                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
    cv2.imshow("Collect eyes", frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()

# Every recording gets its own file, so nothing is ever overwritten
stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
filename = f"{name}_{stamp}.csv"
pd.DataFrame({"ear": rows}).to_csv(filename, index=False)
print("Saved", len(rows), "values to", filename)