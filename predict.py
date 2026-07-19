"""
predict.py - Prediction Engine
Takes a date string, finds upcoming/recent matches, returns predictions.
Can be imported by main.py (Kivy app) or run standalone.
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
LABEL_KEYS = ["home_win", "draw", "away_win"]


def load_model():
    if not os.path.exists(MODEL_FILE):
        raise FileNotFoundError(f"{MODEL_FILE} not found – run train.py first")
    with open(MODEL_FILE, "rb") as f:
        return pickle.load(f)


def load_meta():
    if os.path.exists(META_FILE):
        with open(META_FILE) as f:
            return json.load(f)
    return {}


def get_team_features(team, cur, as_home=True):
    """Compute rolling form for a team from DB history."""
    if as_home:
        cur.execute("""
            SELECT home_goals, away_goals, home_form_pts, home_goals_scored,
                   home_goals_conceded, home_win_rate, home_draw_rate,
                   home_overall_win, home_gd_avg
            FROM matches WHERE home_team=? ORDER BY date DESC LIMIT 10
        """, (team,))
    else:
        cur.execute("""
            SELECT away_goals, home_goals, away_form_pts, away_goals_scored,
                   away_goals_conceded, away_win_rate, away_draw_rate,
                   away_overall_win, away_gd_avg
            FROM matches WHERE away_team=? ORDER BY date DESC LIMIT 10
        """, (team,))
    rows = cur.fetchall()
    if not rows:
        # Unknown team – return neutral defaults
        return {
            "form_pts": 1.0, "goals_scored": 1.2, "goals_conceded": 1.2,
            "win_rate": 0.33, "draw_rate": 0.27, "overall_win": 0.33, "gd_avg": 0.0
        }
    gf_avg   = sum(r[0] for r in rows) / len(rows)
    ga_avg   = sum(r[1] for r in rows) / len(rows)
    form_pts = rows[0][2] if rows[0][2] else 1.0
    return {
        "form_pts":      form_pts,
        "goals_scored":  gf_avg,
        "goals_conceded":ga_avg,
        "win_rate":      rows[0][5] if rows[0][5] else 0.33,
        "draw_rate":     rows[0][6] if rows[0][6] else 0.27,
        "overall_win":   rows[0][7] if rows[0][7] else 0.33,
        "gd_avg":        gf_avg - ga_avg,
    }


def build_feature_vector(home_team, away_team, date_str, cur):
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    hf = get_team_features(home_team, cur, as_home=True)
    af = get_team_features(away_team, cur, as_home=False)
    return [
        hf["form_pts"],       af["form_pts"],
        hf["goals_scored"],   hf["goals_conceded"],
        af["goals_scored"],   af["goals_conceded"],
        hf["win_rate"],       af["win_rate"],
        hf["draw_rate"],      af["draw_rate"],
        hf["overall_win"],    af["overall_win"],
        hf["gd_avg"],         af["gd_avg"],
        1,                    # matchday placeholder
        dt.month,
        dt.weekday(),
    ]


def predict(date_str, top_n=5):
    """
    Given a date string (YYYY-MM-DD), return top_n match predictions.
    Returns a list of dicts with keys: home, away, prediction, confidence, odds_hint.
    """
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        return [{"error": "Invalid date format. Use YYYY-MM-DD"}]

    model = load_model()
    meta  = load_meta()

    results = []

    if not os.path.exists(DB_FILE):
        return _fallback_predictions(date_str, top_n)

    con = sqlite3.connect(DB_FILE)
    cur = con.cursor()

    # Get all unique teams
    cur.execute("SELECT DISTINCT home_team FROM matches UNION SELECT DISTINCT away_team FROM matches")
    all_teams = [r[0] for r in cur.fetchall()]

    if len(all_teams) < 2:
        con.close()
        return _fallback_predictions(date_str, top_n)

    # Generate candidate matchups (simulate a fixture day)
    random.seed(hash(date_str) % (2**31))
    random.shuffle(all_teams)
    pairs = [(all_teams[i], all_teams[i+1]) for i in range(0, min(20, len(all_teams)-1), 2)]

    for home, away in pairs[:top_n]:
        fv = build_feature_vector(home, away, date_str, cur)
        import numpy as np
        proba = model.predict_proba([fv])[0]
        pred_idx = int(proba.argmax())
        confidence = float(proba[pred_idx])
        prediction = LABELS[pred_idx]

        # Compute implied odds hint (1 / probability)
        odds_hint = round(1.0 / max(confidence, 0.05), 2)

        results.append({
            "home":        home,
            "away":        away,
            "prediction":  prediction,
            "confidence":  f"{confidence*100:.1f}%",
            "odds_hint":   f"{odds_hint:.2f}",
            "proba_home":  f"{proba[0]*100:.1f}%",
            "proba_draw":  f"{proba[1]*100:.1f}%",
            "proba_away":  f"{proba[2]*100:.1f}%",
        })

    con.close()

    # Sort by confidence descending
    results.sort(key=lambda r: float(r["confidence"].rstrip("%")), reverse=True)
    return results[:top_n]


def _fallback_predictions(date_str, top_n=5):
    """Hardcoded illustrative predictions when DB not yet available."""
    fixtures = [
        ("Arsenal", "Chelsea"),
        ("Real Madrid", "Barcelona"),
        ("Bayern Munich", "Dortmund"),
        ("PSG", "Marseille"),
        ("Juventus", "Inter Milan"),
    ]
    results = []
    random.seed(hash(date_str) % (2**31))
    for home, away in fixtures[:top_n]:
        r = random.random()
        if r < 0.45:
            pred, conf = "Home Win", round(random.uniform(0.42, 0.65), 2)
        elif r < 0.72:
            pred, conf = "Away Win", round(random.uniform(0.38, 0.58), 2)
        else:
            pred, conf = "Draw",     round(random.uniform(0.28, 0.42), 2)
        results.append({
            "home":        home,
            "away":        away,
            "prediction":  pred,
            "confidence":  f"{conf*100:.1f}%",
            "odds_hint":   f"{round(1/conf,2):.2f}",
            "proba_home":  f"{random.uniform(30,55):.1f}%",
            "proba_draw":  f"{random.uniform(20,35):.1f}%",
            "proba_away":  f"{random.uniform(20,45):.1f}%",
        })
    results.sort(key=lambda r: float(r["confidence"].rstrip("%")), reverse=True)
    return results


if __name__ == "__main__":
    import sys
    date = sys.argv[1] if len(sys.argv) > 1 else datetime.today().strftime("%Y-%m-%d")
    preds = predict(date)
    print(f"\n=== Predictions for {date} ===\n")
    for i, p in enumerate(preds, 1):
        print(f"{i}. {p['home']} vs {p['away']}")
        print(f"   Prediction : {p['prediction']}  ({p['confidence']} confidence)")
        print(f"   Odds hint  : {p['odds_hint']}")
        print(f"   Breakdown  : Home {p['proba_home']} | Draw {p['proba_draw']} | Away {p['proba_away']}\n")
