"""
train.py - XGBoost Model Training
Reads data.db, trains classifier, saves model.pkl + label_encoder.pkl
"""

import sqlite3
import pickle
import os
import json
import numpy as np

FEATURE_COLS = [
    "home_form_pts", "away_form_pts",
    "home_goals_scored", "home_goals_conceded",
    "away_goals_scored", "away_goals_conceded",
    "home_win_rate", "away_win_rate",
    "home_draw_rate", "away_draw_rate",
    "home_overall_win", "away_overall_win",
    "home_gd_avg", "away_gd_avg",
    "matchday", "month", "day_of_week",
]
TARGET_COL = "outcome"
LABELS     = ["home_win", "draw", "away_win"]
MODEL_FILE = "model.pkl"
META_FILE  = "model_meta.json"
DB_FILE    = "data.db"


def load_data(db_path=DB_FILE):
    con = sqlite3.connect(db_path)
    cur = con.cursor()
    cur.execute(f"SELECT {','.join(FEATURE_COLS)}, outcome FROM matches")
    rows = cur.fetchall()
    con.close()

    X, y = [], []
    for row in rows:
        X.append(list(row[:-1]))
        y.append(LABELS.index(row[-1]) if row[-1] in LABELS else -1)

    X = np.array(X, dtype=np.float32)
    y = np.array(y, dtype=np.int32)

    # Remove rows where outcome was unrecognized
    mask = y >= 0
    return X[mask], y[mask]


def train(db_path=DB_FILE):
    try:
        import xgboost as xgb
    except ImportError:
        print("[WARN] xgboost not installed – falling back to sklearn RandomForest")
        from sklearn.ensemble import RandomForestClassifier as Model
        use_xgb = False
    else:
        use_xgb = True

    X, y = load_data(db_path)
    print(f"[INFO] Training on {len(X)} samples, {len(FEATURE_COLS)} features")
    print(f"[INFO] Class distribution: home_win={sum(y==0)}, draw={sum(y==1)}, away_win={sum(y==2)}")

    # Train/test split (80/20)
    split = int(len(X) * 0.8)
    X_train, X_test = X[:split], X[split:]
    y_train, y_test = y[:split], y[split:]

    if use_xgb:
        model = xgb.XGBClassifier(
            n_estimators=200,
            max_depth=6,
            learning_rate=0.05,
            subsample=0.8,
            colsample_bytree=0.8,
            use_label_encoder=False,
            eval_metric="mlogloss",
            random_state=42,
            n_jobs=-1,
        )
    else:
        model = Model(n_estimators=200, random_state=42, n_jobs=-1)

    model.fit(X_train, y_train)

    # Evaluate
    preds = model.predict(X_test)
    accuracy = float(np.mean(preds == y_test))
    print(f"[OK] Test accuracy: {accuracy:.3f} ({accuracy*100:.1f}%)")

    # Per-class accuracy
    for i, label in enumerate(LABELS):
        mask = y_test == i
        if mask.sum() > 0:
            cls_acc = float(np.mean(preds[mask] == y_test[mask]))
            print(f"       {label}: {cls_acc:.3f} ({mask.sum()} samples)")

    # Save model
    with open(MODEL_FILE, "wb") as f:
        pickle.dump(model, f)

    meta = {
        "accuracy":     round(accuracy, 4),
        "n_samples":    len(X),
        "feature_cols": FEATURE_COLS,
        "labels":       LABELS,
        "model_type":   "xgboost" if use_xgb else "randomforest",
    }
    with open(META_FILE, "w") as f:
        json.dump(meta, f, indent=2)

    print(f"[OK] Model saved → {MODEL_FILE}")
    print(f"[OK] Metadata  → {META_FILE}")
    return model, accuracy


if __name__ == "__main__":
    if not os.path.exists(DB_FILE):
        print(f"[ERROR] {DB_FILE} not found. Run clean.py first.")
    else:
        train()
