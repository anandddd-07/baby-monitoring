"""motion.py - body movement detector based on body keypoint motion."""

import json
import math
import os
import sys

import numpy as np

# MediaPipe pose landmark indices we care about. These are on the upper body,
# so the detector works when the camera can see at least the head and shoulders.
UPPER_BODY_POINTS = (0, 11, 12, 13, 14, 15, 16)  # nose, shoulders, elbows, wrists
VISIBILITY_THRESHOLD = 0.5
WINDOW = 30


def _base_dir():
    """Folder that holds the project files, also works inside a packaged app."""
    if getattr(sys, "frozen", False):
        return getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.dirname(os.path.abspath(__file__))


MODEL_PATH = os.path.join(_base_dir(), "motion_model.json")


def _as_keypoints(frame):
    frame = np.asarray(frame, dtype=float).reshape(33, 4)
    return frame


def frame_motion(previous, current):
    """Average distance moved between two frames, only using visible points."""
    previous = _as_keypoints(previous)
    current = _as_keypoints(current)
    mask = (previous[:, 3] >= VISIBILITY_THRESHOLD) & (current[:, 3] >= VISIBILITY_THRESHOLD)
    if not mask.any():
        return 0.0

    deltas = previous[mask, :2] - current[mask, :2]
    return float(np.mean(np.linalg.norm(deltas, axis=1)))


def window_features(window):
    """Build a small feature vector describing how much a 30-frame window moves.

    Features:
      0. mean frame-to-frame motion
      1. largest frame-to-frame motion
      2. largest - smallest motion, so a single movement burst still counts
    """
    window = np.asarray(window, dtype=float)
    if window.shape[0] < 2:
        return [0.0, 0.0, 0.0]

    motions = [frame_motion(window[i], window[i + 1]) for i in range(len(window) - 1)]
    motions = np.asarray(motions, dtype=float)
    return [
        float(np.mean(motions)),
        float(np.max(motions)),
        float(np.max(motions) - np.min(motions)),
    ]


def _load_model():
    if not os.path.isfile(MODEL_PATH):
        return None
    with open(MODEL_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def predict_body(window):
    """Return (probability_of_moving, label) for a 30-frame pose window."""
    model = _load_model()
    features = window_features(window)

    if model is None:
        return features[0], "BODY MOVING" if features[0] > 0.015 else "NO MOVING"

    means = np.asarray(model["means"], dtype=float)
    stds = np.asarray(model["stds"], dtype=float)
    weights = np.asarray(model["weights"], dtype=float)
    stds = np.where(stds == 0.0, 1.0, stds)
    scaled = (np.asarray(features, dtype=float) - means) / stds
    z = float(np.dot(weights, scaled) + model["bias"])
    probability = 1.0 / (1.0 + math.exp(-z))
    label = "BODY MOVING" if probability >= model.get("threshold", 0.5) else "NO MOVING"
    return probability, label
