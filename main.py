import time

import cv2
import numpy as np

from detect_file import Detect_final

WINDOW_NAME = "Baby Monitor"
FONT = cv2.FONT_HERSHEY_SIMPLEX

# Colours are BGR (OpenCV order)
WHITE = (255, 255, 255)
GREEN = (80, 200, 80)
RED = (60, 60, 255)
BLUE = (255, 150, 0)

points = []          # corners of the safe area
detecting = False    # becomes True after pressing D
message = ""
message_until = 0.0


def on_mouse(event, x, y, flags, param):
    if event == cv2.EVENT_LBUTTONDOWN and not detecting:
        points.append([x, y])


def draw_area(frame, color):
    for p in points:
        cv2.circle(frame, (p[0], p[1]), 5, color, -1)
    if len(points) > 1:
        cv2.polylines(frame, [np.int32(points)], detecting, color, 2)


def draw_help(frame, lines):
    """Dark band with instructions at the bottom of the window."""
    h, w = frame.shape[:2]
    band_h = 12 + 28 * len(lines)
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, h - band_h), (w, h), (30, 30, 30), -1)
    frame = cv2.addWeighted(overlay, 0.6, frame, 0.4, 0)
    y = h - band_h + 28
    for line in lines:
        cv2.putText(frame, line, (15, y), FONT, 0.6, WHITE, 1)
        y += 28
    return frame


print("Loading models, please wait...")
model = Detect_final()

cap = cv2.VideoCapture(0)
if not cap.isOpened():
    print("Camera not available. Close other apps that use the camera and try again.")
    raise SystemExit

cv2.namedWindow(WINDOW_NAME)
cv2.setMouseCallback(WINDOW_NAME, on_mouse)

prev = time.time()
fps = 0.0

while True:
    ok, frame = cap.read()
    if not ok:
        print("Could not read from the camera.")
        break

    frame = cv2.flip(frame, 1)   # mirror view, flipped only once

    if detecting:
        frame = model.output(frame, points)

    # The area turns red when the baby is outside, green otherwise
    if detecting:
        area_color = RED if model.label_outside == "OUTSIDE" else GREEN
    else:
        area_color = BLUE
    draw_area(frame, area_color)

    # FPS
    now = time.time()
    if now > prev:
        fps = 0.9 * fps + 0.1 * (1.0 / (now - prev))
    prev = now
    h, w = frame.shape[:2]
    cv2.putText(frame, "FPS: %d" % fps, (w - 110, 30), FONT, 0.6, WHITE, 2)

    if detecting:
        cv2.putText(frame, "R: new area   Q: quit", (w - 230, 55),
                    FONT, 0.5, WHITE, 1)
    else:
        frame = draw_help(frame, [
            "1. Left-click 3 or more points to draw the safe area",
            "2. Press D to start detection",
            "R: clear points   Q: quit",
        ])
        if time.time() < message_until:
            cv2.putText(frame, message, (15, 40), FONT, 0.8, RED, 2)

    cv2.imshow(WINDOW_NAME, frame)

    key = cv2.waitKey(1) & 0xFF
    if key == ord('q'):
        break
    elif key == ord('r'):
        points.clear()
        detecting = False
        model.reset()
    elif key == ord('d') and not detecting:
        if len(points) >= 3:
            points.append(points[0])   # close the shape
            detecting = True
        else:
            message = "Click at least 3 points first"
            message_until = time.time() + 2.0

cap.release()
cv2.destroyAllWindows()
