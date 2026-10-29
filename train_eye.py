"""
train_eye.py - trains the eye-state model (Random Forest, classic ML).

It uses EVERY recording it finds:
    Eyes_Open*.csv   -> label 1 (WAKE UP)
    Eyes_Closed*.csv -> label 0 (SLEEPING)
so old and new recordings are combined automatically.

The model summarises each 30-frame window into five classic-ML features:
    mean, std, min, max, last EAR value
and trains a scikit-learn Random Forest on them. The saved file is a
small eye_model.joblib that loads in milliseconds.
"""
import glob

import numpy as np
import pandas as pd
from joblib import dump
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, confusion_matrix

STEPS = 30   # same window length that detect_file.py uses


def window_features(win):
    """Turn one 30-frame EAR window into the 5 features the model sees."""
    win = np.asarray(win, dtype=float)
    return np.array([
        win.mean(),        # average openness over the window
        win.std(),         # how much it varied (blinks, drowsiness)
        win.min(),         # most closed moment
        win.max(),         # most open moment
        win[-1],           # where the window ended
    ])


def make_windows(csv_name, label):
    ear = pd.read_csv(csv_name)["ear"].values
    X = np.array([window_features(ear[i - STEPS:i])
                  for i in range(STEPS, len(ear))])
    y = np.full(len(X), label)
    return X, y


def split(X, y):
    # Time-based split with a gap, so train and test windows never overlap
    cut = int(len(X) * 0.8)
    return X[:cut], y[:cut], X[cut + STEPS:], y[cut + STEPS:]


X_train, y_train, X_test, y_test = [], [], [], []

for pattern, label in [("Eyes_Open*.csv", 1), ("Eyes_Closed*.csv", 0)]:
    for path in sorted(glob.glob(pattern)):
        X, y = make_windows(path, label)
        if len(X) < 100:
            print("Skipping (too short):", path)
            continue
        a, b, c, d = split(X, y)
        X_train.append(a); y_train.append(b)
        X_test.append(c);  y_test.append(d)
        print("Using", path, "->", len(X), "windows, label", label)

if not X_train:
    raise SystemExit("No CSV files found. Record data with collect_eye.py first.")

X_train = np.concatenate(X_train); y_train = np.concatenate(y_train)
X_test = np.concatenate(X_test);   y_test = np.concatenate(y_test)
print("Train:", X_train.shape, "Test:", X_test.shape)

model = RandomForestClassifier(
    n_estimators=200,
    max_depth=None,
    class_weight="balanced",
    n_jobs=-1,
    random_state=42,
)
model.fit(X_train, y_train)

pred = model.predict(X_test)
acc = accuracy_score(y_test, pred)
print("Test accuracy:", round(float(acc), 4))

# Confusion matrix: which kind of mistake does the model make?
tn = int(((pred == 0) & (y_test == 0)).sum())
fp = int(((pred == 1) & (y_test == 0)).sum())
fn = int(((pred == 0) & (y_test == 1)).sum())
tp = int(((pred == 1) & (y_test == 1)).sum())
print("Confusion matrix (rows = real, columns = predicted)")
print("                SLEEPING   WAKE UP")
print("real SLEEPING   %8d  %8d" % (tn, fp))
print("real WAKE UP    %8d  %8d" % (fn, tp))

dump(model, "eye_model.joblib")
print("Saved eye_model.joblib")
