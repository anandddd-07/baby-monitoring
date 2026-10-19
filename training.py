"""
training.py - trains the body-movement model (model.h5).

It uses EVERY recording it finds:
    No_Moving*.csv  -> label 0 (not moving)
    Moving*.csv     -> label 1 (moving)
so old and new recordings are combined automatically.
"""
import glob

import numpy as np
import pandas as pd
from keras.layers import Input, LSTM, Dense, Dropout
from keras.models import Sequential

STEPS = 30   # frames per window (same as detect_file.py)


def make_windows(csv_name, label):
    # Windows are built inside ONE file, so they never mix two recordings
    data = pd.read_csv(csv_name, index_col=0).values
    X = np.array([data[i - STEPS:i] for i in range(STEPS, len(data))])
    y = np.full(len(X), label)
    return X, y


def split(X, y):
    # Time-based split: first 80% to train, last 20% to test, with a gap
    # so that train and test windows never overlap.
    cut = int(len(X) * 0.8)
    return X[:cut], y[:cut], X[cut + STEPS:], y[cut + STEPS:]


X_train, y_train, X_test, y_test = [], [], [], []

for pattern, label in [("No_Moving*.csv", 0), ("Moving*.csv", 1)]:
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
    raise SystemExit("No CSV files found. Record data with collect_body.py first.")

X_train = np.concatenate(X_train); y_train = np.concatenate(y_train)
X_test = np.concatenate(X_test);   y_test = np.concatenate(y_test)

order = np.random.permutation(len(X_train))
X_train, y_train = X_train[order], y_train[order]
print("Train:", X_train.shape, "Test:", X_test.shape)

model = Sequential()
model.add(Input(shape=(X_train.shape[1], X_train.shape[2])))
model.add(LSTM(units=50, return_sequences=True))
model.add(Dropout(0.2))
model.add(LSTM(units=50, return_sequences=True))
model.add(Dropout(0.2))
model.add(LSTM(units=50, return_sequences=True))
model.add(Dropout(0.2))
model.add(LSTM(units=50))
model.add(Dropout(0.2))
model.add(Dense(units=1, activation="sigmoid"))
model.compile(optimizer="adam", metrics=["accuracy"], loss="binary_crossentropy")

model.fit(X_train, y_train, epochs=16, batch_size=32,
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
print("               NO MOVING   MOVING")
print("real NO MOVING  %7d  %7d" % (tn, fp))
print("real MOVING     %7d  %7d" % (fn, tp))

model.save("model.h5")
print("Saved model.h5")