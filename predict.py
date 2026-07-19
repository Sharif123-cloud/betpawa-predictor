"""
predict.py - Prediction Engine
Runs on the SERVER (GitHub Actions) only — not on Android device.
Generates predictions.json which gets bundled into the APK.
"""

import pickle
import json
import sqlite3
import os
import random
from datetime import datetime, timedelta

MODEL_FILE   = "model.pkl"
META_FILE    = "model_meta.json"
DB_FILE      = "data.db"
OUTPUT_JSON  = "predictions.json"

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
LABELS = ["Home Win", "Draw", "Away Win"]


def load_model():
    with open(MODEL_FILE, "rb") as f:
        return pickle.load(f)


def get_team_features(team, cur):
    cur.execute("""
        SELECT home_goals, away_goals, home_form_pts, home_goals_scored,
               home_goals_conceded, home_win_rate, home_draw_rate,
               home_overall_win, home_gd_avg
        FROM matches WHERE home_team=? ORDER BY date DESC LIMIT 10
    """, (team,))
    rows = cur.fetchall()
    if not rows:
        cur.execute("""
            SELECT away_goals, home_goals, away_form_pts, away_goals_scored,
                   away_goals_conceded, away_win_rate, away_draw_rate,
                   away_overall_win, away_gd_avg
            FROM matches WHERE away_team=? ORDER BY date DESC LIMIT 10
        """, (team,))
        rows = cur.fetchall()
    if not rows:
        return {
            "form_pts": 1.0, "goals_scored": 1.2, "goals_conceded": 1.2,
            "win_rate": 0.33, "draw_rate": 0.27, "overall_win": 0.33, "gd_avg": 0.0
        }
    gf_avg = sum(r[0] for r in rows) / len(rows)
    ga_avg = sum(r[1] for r in rows) / len(rows)
    return {
        "form_pts":       rows[0][2] if rows[0][2] else 1.0,
        "goals_scored":   gf_avg,
        "goals_conceded": ga_avg,
        "win_rate":       rows[0][5] if rows[0][5] else 0.33,
        "draw_rate":      rows[0][6] if rows[0][6] else 0.27,
        "overall_win":    rows[0][7] if rows[0][7] else 0.33,
        "gd_avg":         gf_avg - ga_avg,
    }


def predict_for_date(date_str, model, cur, top_n=5):
    import numpy as np
    dt = datetime.strptime(date_str, "%Y-%m-%d")

    cur.execute("SELECT DISTINCT home_team FROM matches UNION SELECT DISTINCT away_team FROM matches")
    all_teams = [r[0] for r in cur.fetchall()]
    if len(all_teams) < 2:
        return _fallback_predictions(date_str, top_n)

    random.seed(hash(date_str) % (2**31))
    random.shuffle(all_teams)
    pairs = [(all_teams[i], all_teams[i+1]) for i in range(0, min(20, len(all_teams)-1), 2)]

    results = []
    for home, away in pairs[:top_n]:
        hf = get_team_features(home, cur)
        af = get_team_features(away, cur)
        fv = [
            hf["form_pts"],       af["form_pts"],
            hf["goals_scored"],   hf["goals_conceded"],
            af["goals_scored"],   af["goals_conceded"],
            hf["win_rate"],       af["win_rate"],
            hf["draw_rate"],      af["draw_rate"],
            hf["overall_win"],    af["overall_win"],
            hf["gd_avg"],         af["gd_avg"],
            1, dt.month, dt.weekday(),
        ]
        proba    = model.predict_proba([fv])[0]
        pred_idx = int(proba.argmax())
        conf     = float(proba[pred_idx])
        results.append({
            "home":        home,
            "away":        away,
            "prediction":  LABELS[pred_idx],
            "confidence":  f"{conf*100:.1f}%",
            "odds_hint":   f"{round(1.0/max(conf,0.05), 2):.2f}",
            "proba_home":  f"{proba[0]*100:.1f}%",
            "proba_draw":  f"{proba[1]*100:.1f}%",
            "proba_away":  f"{proba[2]*100:.1f}%",
        })
    results.sort(key=lambda r: float(r["confidence"].rstrip("%")), reverse=True)
    return results[:top_n]


def _fallback_predictions(date_str, top_n=5):
    fixtures = [
        ("Arsenal", "Chelsea"),
        ("Real Madrid", "Barcelona"),
        ("Bayern Munich", "Dortmund"),
        ("PSG", "Marseille"),
        ("Juventus", "Inter Milan"),
    ]
    random.seed(hash(date_str) % (2**31))
    results = []
    for home, away in fixtures[:top_n]:
        r = random.random()
        if r < 0.45:
            pred, conf = "Home Win", round(random.uniform(0.42, 0.65), 2)
        elif r < 0.72:
            pred, conf = "Away Win", round(random.uniform(0.38, 0.58), 2)
        else:
            pred, conf = "Draw",     round(random.uniform(0.28, 0.42), 2)
        results.append({
            "home": home, "away": away,
            "prediction": pred,
            "confidence": f"{conf*100:.1f}%",
            "odds_hint":  f"{round(1/conf,2):.2f}",
            "proba_home": f"{random.uniform(30,55):.1f}%",
            "proba_draw": f"{random.uniform(20,35):.1f}%",
            "proba_away": f"{random.uniform(20,45):.1f}%",
        })
    results.sort(key=lambda r: float(r["confidence"].rstrip("%")), reverse=True)
    return results


def generate_all_predictions(days=45, output=OUTPUT_JSON):
    """
    Pre-generate predictions for `days` days (past 7 + next 38).
    Saves to predictions.json — this file gets bundled into the APK.
    """
    meta = {}
    if os.path.exists(META_FILE):
        with open(META_FILE) as f:
            meta = json.load(f)

    all_predictions = {}

    if os.path.exists(MODEL_FILE) and os.path.exists(DB_FILE):
        model = load_model()
        con   = sqlite3.connect(DB_FILE)
        cur   = con.cursor()

        today = datetime.today()
        start = today - timedelta(days=7)
        for i in range(days):
            d    = start + timedelta(days=i)
            dstr = d.strftime("%Y-%m-%d")
            all_predictions[dstr] = predict_for_date(dstr, model, cur)

        con.close()
        print(f"[OK] Generated predictions for {len(all_predictions)} dates using trained model")
    else:
        print("[WARN] Model or DB not found — using fallback predictions")
        today = datetime.today()
        start = today - timedelta(days=7)
        for i in range(days):
            d    = start + timedelta(days=i)
            dstr = d.strftime("%Y-%m-%d")
            all_predictions[dstr] = _fallback_predictions(dstr)

    bundle = {
        "generated_at":  datetime.today().strftime("%Y-%m-%d %H:%M UTC"),
        "model_accuracy": meta.get("accuracy", "N/A"),
        "model_type":     meta.get("model_type", "fallback"),
        "n_samples":      meta.get("n_samples", 0),
        "predictions":    all_predictions,
    }

    with open(output, "w") as f:
        json.dump(bundle, f, indent=2)

    print(f"[OK] Saved → {output}  ({len(all_predictions)} dates, ~{days} day window)")
    return bundle


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--generate":
        generate_all_predictions()
    else:
        date = sys.argv[1] if len(sys.argv) > 1 else datetime.today().strftime("%Y-%m-%d")
        if os.path.exists(MODEL_FILE) and os.path.exists(DB_FILE):
            model = load_model()
            con   = sqlite3.connect(DB_FILE)
            cur   = con.cursor()
            preds = predict_for_date(date, model, cur)
            con.close()
        else:
            preds = _fallback_predictions(date)
        print(f"\n=== Predictions for {date} ===\n")
        for i, p in enumerate(preds, 1):
            print(f"{i}. {p['home']} vs {p['away']}")
            print(f"   → {p['prediction']}  ({p['confidence']} confidence, odds hint: {p['odds_hint']})")
            print(f"   Home {p['proba_home']} | Draw {p['proba_draw']} | Away {p['proba_away']}\n")
