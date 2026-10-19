"""
train_eye.py - trains the eye-state model (model30.h5).

It uses EVERY recording it finds:
    Eyes_Open*.csv   -> label 1 (WAKE UP)
    Eyes_Closed*.csv -> label 0 (SLEEPING)
so old and new recordings are combined automatically.
"""
import glob

import numpy as np
import pandas as pd
from keras.layers import Input, LSTM, Dense, Dropout
from keras.models import Sequential

STEPS = 30   # same window length that detect_file.py uses


def make_windows(csv_name, label):
    ear = pd.read_csv(csv_name)["ear"].values
    X = np.array([ear[i - STEPS:i] for i in range(STEPS, len(ear))])
    X = X.reshape(-1, STEPS, 1)
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

order = np.random.permutation(len(X_train))
X_train, y_train = X_train[order], y_train[order]
print("Train:", X_train.shape, "Test:", X_test.shape)

model = Sequential()
model.add(Input(shape=(STEPS, 1)))
model.add(LSTM(32))
model.add(Dropout(0.2))
model.add(Dense(1, activation="sigmoid"))
model.compile(optimizer="adam", loss="binary_crossentropy", metrics=["accuracy"])

model.fit(X_train, y_train, epochs=20, batch_size=32,
          validation_data=(X_test, y_test))

loss, acc = model.evaluate(X_test, y_test, verbose=0)
print("Test accuracy:", acc)

# Confusion matrix: which kind of mistake does the model make?
pred = (model.predict(X_test, verbose=0).ravel() > 0.5).astype(int)
tn = int(((pred == 0) & (y_test == 0)).sum())
fp = int(((pred == 1) & (y_test == 0)).sum())
fn = int(((pred == 0) & (y_test == 1)).sum())
tp = int(((pred == 1) & (y_test == 1)).sum())
print("Confusion matrix (rows = real, columns = predicted)")
print("                SLEEPING   WAKE UP")
print("real SLEEPING   %8d  %8d" % (tn, fp))
print("real WAKE UP    %8d  %8d" % (fn, tp))

model.save("model30.h5")
print("Saved model30.h5")