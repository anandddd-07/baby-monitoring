"""
detect_file.py

Runs three checks on every webcam frame:
  1. Eyes : EAR value  -> Random Forest (eye_model.joblib) -> SLEEPING / AWAKE
  2. Body : pose points -> motion model + OpenCV frame difference -> NO MOVING / BODY MOVING
  3. Area : body points against user-drawn polygon -> INSIDE / OUTSIDE
"""
import os
import sys
import time
import threading
from collections import deque

import cv2
import numpy as np
import mediapipe as mp
import joblib
from shapely.geometry import Point
from shapely.geometry.polygon import Polygon

from voice import voice_Alert_Wakeup, voice_Alert_Outside, voice_Alert_Moving, voice_Alert_Calm
from motion import predict_body

mp_holistic = mp.solutions.holistic
mp_face_mesh = mp.solutions.face_mesh
mp_drawing = mp.solutions.drawing_utils

FONT = cv2.FONT_HERSHEY_SIMPLEX

GREEN = (80, 200, 80)
ORANGE = (0, 165, 255)
RED = (60, 60, 255)
GREY = (200, 200, 200)
WHITE = (255, 255, 255)

LEFT_EYE = [362, 385, 387, 263, 373, 380]
RIGHT_EYE = [33, 160, 158, 133, 153, 144]

WINDOW = 30
PREDICT_EVERY = 10
ALERT_EVERY = 15


def _base_dir():
    """Folder that holds the project files, also works inside a packaged app."""
    if getattr(sys, "frozen", False):
        return getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.dirname(os.path.abspath(__file__))


BASE_DIR = _base_dir()
EYE_MODEL_PATH = os.path.join(BASE_DIR, "eye_model.joblib")


def load_eye_model(path):
    """Load the eye classifier (Random Forest, classic ML).

    Returns None if the file is missing so the rest of the app keeps
    working with a simple EAR-threshold fallback.
    """
    try:
        return joblib.load(path)
    except (OSError, ValueError):
        return None


def distance(p1, p2):
    return ((p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2) ** 0.5


def eye_points(landmarks, idxs, w, h):
    return [(int(landmarks[i].x * w), int(landmarks[i].y * h)) for i in idxs]


def ear_from_points(pts):
    vertical = distance(pts[1], pts[5]) + distance(pts[2], pts[4])
    horizontal = 2.0 * distance(pts[0], pts[3])
    return vertical / horizontal if horizontal > 0 else 0.0


class Detect_final:
    def __init__(self):
        self.model_eye = load_eye_model(EYE_MODEL_PATH)

        self.face_mesh = mp_face_mesh.FaceMesh(
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5,
        )
        self.holistic = mp_holistic.Holistic(
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5,
        )

        self.body_seq = deque(maxlen=WINDOW)
        self.ear_seq = deque(maxlen=WINDOW)
        self.body_count = 0
        self.ear_count = 0
        self.busy_eye = False
        self.prev_gray = None
        self.frame_diff_scores = deque(maxlen=WINDOW)

        self.motion_threshold = 0.03
        self.label = "Waiting"
        self.label_eye = "Waiting"
        self.label_outside = "Waiting"
        self.ear = 0.0
        self.body_probability = 0.0
        self.eye_probability = 0.0
        self.motion_level = 0.0
        self.last_alert = {}

    def reset(self):
        self.body_seq.clear()
        self.ear_seq.clear()
        self.body_count = 0
        self.ear_count = 0
        self.frame_diff_scores.clear()
        self.prev_gray = None
        self.body_probability = 0.0
        self.eye_probability = 0.0
        self.motion_level = 0.0
        self.label = "Waiting"
        self.label_eye = "Waiting"
        self.label_outside = "Waiting"

    def _predict_eye(self, seq):
        try:
            seq = np.asarray(seq, dtype=float)
            # Same 5 features the Random Forest was trained on:
            # mean, std, min, max, last EAR value of the 30-frame window.
            x = np.array([[
                seq.mean(), seq.std(), seq.min(), seq.max(), seq[-1],
            ]], dtype=float)
            if self.model_eye is None:
                # Fallback: classic EAR threshold if the model file is missing.
                p = 1.0 if seq.mean() > 0.18 else 0.0
            else:
                p = float(self.model_eye.predict_proba(x)[0][1])
            self.eye_probability = p
            self.label_eye = "AWAKE" if p > 0.5 else "SLEEPING"
        finally:
            self.busy_eye = False

    def _alert(self, name, func):
        now = time.time()
        if now - self.last_alert.get(name, 0) > ALERT_EVERY:
            self.last_alert[name] = now
            threading.Thread(target=func, daemon=True).start()

    def check_area(self, pose_landmarks, points, w, h):
        if len(points) < 3:
            return "NO AREA"
        if not pose_landmarks:
            return "NO BODY"
        try:
            polygon = Polygon(points)
        except ValueError:
            return "NO AREA"

        pl = mp_holistic.PoseLandmark
        ids = [pl.NOSE, pl.LEFT_INDEX, pl.RIGHT_INDEX,
               pl.LEFT_FOOT_INDEX, pl.RIGHT_FOOT_INDEX]
        landmarks = pose_landmarks.landmark
        seen = 0
        for i in ids:
            p = landmarks[i.value]
            if p.visibility < 0.5:
                continue
            seen += 1
            if not polygon.contains(Point(int(p.x * w), int(p.y * h))):
                return "OUTSIDE"
        return "INSIDE" if seen > 0 else "NO BODY"

    @staticmethod
    def color_for(value):
        if value in ("SLEEPING", "NO MOVING", "INSIDE"):
            return GREEN
        if value in ("AWAKE", "BODY MOVING"):
            return ORANGE
        if value == "OUTSIDE":
            return RED
        return GREY

    def draw_panel(self, frame):
        overlay = frame.copy()
        cv2.rectangle(overlay, (10, 10), (310, 145), (30, 30, 30), -1)
        frame = cv2.addWeighted(overlay, 0.6, frame, 0.4, 0)

        rows = [("Eyes", self.label_eye),
                ("Body", self.label),
                ("Area", self.label_outside)]
        y = 40
        for name, value in rows:
            cv2.putText(frame, name + ":", (20, y), FONT, 0.7, WHITE, 2)
            cv2.putText(frame, value, (110, y), FONT, 0.7, self.color_for(value), 2)
            y += 30
        cv2.putText(frame, "EAR: %.2f" % self.ear, (20, y), FONT, 0.6, GREY, 1)

        return self.draw_banner(frame)

    def draw_banner(self, frame):
        """Red banner at the bottom when the baby is outside the safe area."""
        if self.label_outside == "OUTSIDE":
            h, w = frame.shape[:2]
            cv2.rectangle(frame, (0, h - 50), (w, h), RED, -1)
            cv2.putText(frame, "ALERT: OUTSIDE THE SAFE AREA", (20, h - 15),
                        FONT, 0.9, WHITE, 2)
        return frame

    def output(self, frame, points):
                # safety defaults: create any missing settings once
        _defaults = {
            "recent_area": deque(maxlen=5),
            "show_panel": False,
            "voice_enabled": True,
            "eye_probability": 0.0,
            "body_probability": 0.0,
            "motion_level": 0.0,
            "motion_threshold": 0.03,
            "body_threshold_override": None,
        }
        for _k, _v in _defaults.items():
            if not hasattr(self, _k):
                setattr(self, _k, _v)
        h, w, _ = frame.shape
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        rgb.flags.writeable = False
        face_results = self.face_mesh.process(rgb)
        body_results = self.holistic.process(rgb)

        if face_results.multi_face_landmarks:
            lms = face_results.multi_face_landmarks[0].landmark
            left = eye_points(lms, LEFT_EYE, w, h)
            right = eye_points(lms, RIGHT_EYE, w, h)
            self.ear = (ear_from_points(left) + ear_from_points(right)) / 2.0
            self.ear_seq.append(self.ear)
            self.ear_count += 1
            for p in left + right:
                cv2.circle(frame, p, 2, GREEN, -1)

            if (len(self.ear_seq) == WINDOW
                    and self.ear_count % PREDICT_EVERY == 0
                    and not self.busy_eye):
                self.busy_eye = True
                threading.Thread(target=self._predict_eye,
                                 args=(list(self.ear_seq),), daemon=True).start()
        else:
            self.ear_seq.clear()
            self.ear_count = 0
            self.label_eye = "NO FACE"

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (5, 5), 0)
        if self.prev_gray is not None:
            diff = cv2.absdiff(self.prev_gray, gray)
            _, mask = cv2.threshold(diff, 25, 255, cv2.THRESH_BINARY)
            pixel_motion = cv2.countNonZero(mask) / float(mask.size)
        else:
            pixel_motion = 0.0
        self.frame_diff_scores.append(pixel_motion)
        self.motion_level = pixel_motion
        self.prev_gray = gray

        if body_results.pose_landmarks:
            keypoints = np.array(
                [[p.x, p.y, p.z, p.visibility]
                 for p in body_results.pose_landmarks.landmark]).flatten()
        else:
            keypoints = np.zeros(33 * 4)
        self.body_seq.append(keypoints)
        self.body_count += 1

        if (len(self.body_seq) == WINDOW
                and self.body_count % PREDICT_EVERY == 0):
            body_probability, body_label = predict_body(list(self.body_seq))

            open_cv_says_moving = (
                len(self.frame_diff_scores) > 0
                and max(self.frame_diff_scores) >= getattr(self, "motion_threshold", 0.03)
            )

            self.body_probability = float(body_probability)
            self.label = "BODY MOVING" if (
                body_label == "BODY MOVING" or open_cv_says_moving
            ) else "NO MOVING"

        mp_drawing.draw_landmarks(
            frame, body_results.pose_landmarks, mp_holistic.POSE_CONNECTIONS,
            mp_drawing.DrawingSpec(color=GREY, thickness=1, circle_radius=2),
            mp_drawing.DrawingSpec(color=(120, 120, 120), thickness=1))

        raw_area = self.check_area(body_results.pose_landmarks,
                           points, w, h)
        if not hasattr(self, "recent_area"):
            self.recent_area = deque(maxlen=5)
        self.recent_area.append(raw_area)
        if raw_area in ("INSIDE", "OUTSIDE"):
            # majority of the last 5 checks, so one noisy frame cannot flip it
            outs = sum(1 for a in self.recent_area if a == "OUTSIDE")
            ins = sum(1 for a in self.recent_area if a == "INSIDE")
            self.label_outside = "OUTSIDE" if outs > ins else "INSIDE"
        else:
            self.label_outside = raw_area

        if self.label_outside == "OUTSIDE":
            self._alert("outside", voice_Alert_Outside)
        if self.label == "BODY MOVING":
            self._alert("moving", voice_Alert_Moving)
        if self.label_eye == "AWAKE":
            self._alert("wakeup", voice_Alert_Wakeup)

        if (self.label == "NO MOVING"
                and self.label_eye == "SLEEPING"
                and self.label_outside == "INSIDE"):
            self._alert("calm", voice_Alert_Calm)

        if getattr(self, "show_panel", False):
            return self.draw_panel(frame)
        return self.draw_banner(frame)
