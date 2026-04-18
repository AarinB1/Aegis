import pandas as pd, os, librosa, numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report
from collections import Counter

df = pd.read_csv("LS.csv")
df = df[['Lung Sound ID','Lung Sound Type']].copy()

def feat(p):
    y, sr = librosa.load(p, sr=16000)
    mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13)
    return np.concatenate([np.mean(mfcc, axis=1), np.std(mfcc, axis=1)])

X, y = [], []
failed = []

for _, r in df.iterrows():
    name = r['Lung Sound ID'].strip() + '.wav'
    path = os.path.join("LS", name)
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

test_file = "LS/M_R_LLA.wav"
label, conf = predict_audio(test_file)

if label == "distress":
    if conf > 0.7:
        print(f"AIRWAY COMPROMISE ({conf:.2f})")
    else:
        print(f"POSSIBLE AIRWAY COMPROMISE ({conf:.2f})")
else:
    print(f"NORMAL ({conf:.2f})")