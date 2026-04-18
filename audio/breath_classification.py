import pandas as pd, os, librosa, numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report
from collections import Counter

df = pd.read_csv("LS.csv")
df = df[['Lung Sound ID','Lung Sound Type']].copy()

from scipy.signal import butter, lfilter

def highpass(y, sr, cutoff=500):
    b, a = butter(4, cutoff / (0.5 * sr), btype='high')
    return lfilter(b, a, y)

def feat(p):
    y, sr = librosa.load(p, sr=16000)
    y = highpass(y, sr)
    y = y / (np.max(np.abs(y)) + 1e-6)

    mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13)
    zcr = np.mean(librosa.feature.zero_crossing_rate(y))
    spec_centroid = np.mean(librosa.feature.spectral_centroid(y=y, sr=sr))
    energy = np.mean(np.abs(y))

    return np.concatenate([
        np.mean(mfcc, axis=1),
        np.std(mfcc, axis=1),
        [zcr, spec_centroid, energy]
    ])
X, y = [], []
failed = []

for _, r in df.iterrows():
    name = r['Lung Sound ID'].strip() + '.wav'
    path = os.path.join("LS", "selected_data", name)
    try:
        X.append(feat(path))
        label = r['Lung Sound Type']
        if label == "Normal":
            y.append("normal")
        else:
            y.append("distress")
    except:
        failed.append(name)

print("Failed count:", len(failed))
print("Class counts:", Counter(y))

used_files = []

for _, r in df.iterrows():
    name = r['Lung Sound ID'].strip() + '.wav'
    path = os.path.join("LS", "selected_data", name)
    try:
        label = "normal" if r['Lung Sound Type'] == "Normal" else "distress"
        used_files.append((name, label))
    except:
        pass

print("\n=== TRAINING FILES ===")
for f, l in used_files:
    print(f"{f} -> {l}")

Xtr, Xte, ytr, yte = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

clf = RandomForestClassifier(class_weight="balanced", random_state=42)
clf.fit(Xtr, ytr)

preds = clf.predict(Xte)
print(classification_report(yte, preds, zero_division=0))

def predict_audio(path):
    f = feat(path)
    pred = clf.predict([f])[0]
    probs = clf.predict_proba([f])[0]
    conf = np.max(probs)
    return pred, conf

def smart_decision(path):
    y, sr = librosa.load(path, sr=16000)
    y = y / (np.max(np.abs(y)) + 1e-6)

    zcr = np.mean(librosa.feature.zero_crossing_rate(y))
    spec_centroid = np.mean(librosa.feature.spectral_centroid(y=y, sr=sr))
    energy = np.mean(np.abs(y))

    # 🔴 tuned thresholds (based on YOUR data)
    if zcr > 0.06 or spec_centroid > 800:
        return "distress", 0.9

    if energy < 0.02:
        return "normal", 0.9

    # fallback to model
    return predict_audio(path)

test_file = "testclip.wav"
label, conf = smart_decision(test_file)

if label == "distress":
    if conf > 0.7:
        print(f"AIRWAY COMPROMISE ({conf:.2f})")
    else:
        print(f"POSSIBLE AIRWAY COMPROMISE ({conf:.2f})")
else:
    print(f"NORMAL ({conf:.2f})")

test_file = "normal.wav"


label, conf = smart_decision(test_file)

if label == "distress":
    if conf > 0.7:
        print(f"AIRWAY COMPROMISE ({conf:.2f})")
    else:
        print(f"POSSIBLE AIRWAY COMPROMISE ({conf:.2f})")
else:
    print(f"NORMAL ({conf:.2f})")