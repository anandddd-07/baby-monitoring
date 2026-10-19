import sys
import time
from datetime import datetime

import cv2
import numpy as np
import pandas as pd
import mediapipe as mp

print("Script started")

# Usage: python collect_body.py Moving   OR   python collect_body.py No_Moving
name = sys.argv[1]
TOTAL_FRAMES = 1200

mp_holistic = mp.solutions.holistic
mp_drawing = mp.solutions.drawing_utils


def extract_keypoints(results):
    if results.pose_landmarks:
        return np.array([[p.x, p.y, p.z, p.visibility]
                         for p in results.pose_landmarks.landmark]).flatten()
    return np.zeros(33 * 4)


cap = cv2.VideoCapture(0)
rows = []

with mp_holistic.Holistic(min_detection_confidence=0.5,
                          min_tracking_confidence=0.5) as holistic:
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
        cv2.imshow("Collect", frame)
        cv2.waitKey(1)

    while len(rows) < TOTAL_FRAMES:
        ret, frame = cap.read()
        if not ret:
            break
        frame = cv2.flip(frame, 1)
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = holistic.process(rgb)
        rows.append(extract_keypoints(results))

        mp_drawing.draw_landmarks(frame, results.pose_landmarks,
                                  mp_holistic.POSE_CONNECTIONS)
        cv2.putText(frame, f"{name}: {len(rows)}/{TOTAL_FRAMES}", (30, 40),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        cv2.imshow("Collect", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

cap.release()
cv2.destroyAllWindows()

# Every recording gets its own file, so nothing is ever overwritten
stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
filename = f"{name}_{stamp}.csv"
pd.DataFrame(rows).to_csv(filename)
print("Saved", len(rows), "frames to", filename)