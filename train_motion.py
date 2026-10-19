"""train_motion.py - train the body movement detector.

Run with:
    ..\\venv311\\Scripts\\python.exe train_motion.py

It reads every No_Moving*.csv and Moving*.csv file in this folder,
including recordings made earlier and new timestamped ones.
"""

import glob
import os

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, confusion_matrix
from sklearn.preprocessing import StandardScaler

from motion import WINDOW, window_features

PROJECT = os.path.dirname(os.path.abspath(__file__))
WINDOW_SIZE = WINDOW


def load_samples(pattern, label):
    files = sorted(glob.glob(os.path.join(PROJECT, pattern)))
    X = []
    y = []
    for filename in files:
        print("  reading", os.path.basename(filename))
        df = pd.read_csv(filename)
        # Drop the header row and the row-number column, as in training.py.
        data = df.iloc[1:, 1:].values
        for i in range(WINDOW_SIZE, len(data)):
            x = window_features(data[i - WINDOW_SIZE:i])
            X.append(x)
            y.append(label)
    return X, y, len(files)


print("Body data files:")
X_still, y_still, n_still = load_samples("No_Moving*.csv", 0)
X_move, y_move, n_move = load_samples("Moving*.csv", 1)

print()
print("Found", n_still, "still file(s) and", n_move, "moving file(s)")
if n_still == 0 or n_move == 0:
    raise SystemExit("Need at least one No_Moving*.csv and one Moving*.csv file.")

X_still = np.array(X_still)
y_still = np.array(y_still)
X_move = np.array(X_move)
y_move = np.array(y_move)

# Time-based split, with a gap so train and test windows do not overlap.
def time_split(X, y, window):
    cut = int(len(X) * 0.8)
    train_idx = list(range(0, cut))
    test_idx = list(range(cut + window, len(X)))
    return train_idx, test_idx

still_train, still_test = time_split(X_still, y_still, WINDOW_SIZE)
move_train, move_test = time_split(X_move, y_move, WINDOW_SIZE)

X_train = np.vstack([X_still[still_train], X_move[move_train]])
y_train = np.concatenate([y_still[still_train], y_move[move_train]])
X_test = np.vstack([X_still[still_test], X_move[move_test]])
y_test = np.concatenate([y_still[still_test], y_move[move_test]])

print("Training samples:", len(X_train), "Test samples:", len(X_test))

scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)

model = LogisticRegression(max_iter=1000, class_weight="balanced")
model.fit(X_train_scaled, y_train)

predictions = model.predict(X_test_scaled)
acc = accuracy_score(y_test, predictions)
print()
print("Test accuracy:", round(float(acc), 4))
print("Confusion matrix (rows = true, cols = predicted, 0 = still, 1 = moving):")
print(confusion_matrix(y_test, predictions))

model_data = {
    "feature_names": ["mean_motion", "max_motion", "motion_spread"],
    "means": scaler.mean_.tolist(),
    "stds": scaler.scale_.tolist(),
    "weights": model.coef_[0].tolist(),
    "bias": float(model.intercept_[0]),
    "threshold": 0.5,
}

import json

output_path = os.path.join(PROJECT, "motion_model.json")
with open(output_path, "w", encoding="utf-8") as f:
    json.dump(model_data, f, indent=2)
print()
print("Saved movement model to", output_path)
