"""
clean.py - Data Cleaning & Feature Engineering Pipeline
Reads raw.csv, engineers features, saves to data.db (SQLite)
"""

import csv
import sqlite3
import os
from datetime import datetime
from collections import defaultdict


INPUT_FILE  = "raw.csv"
OUTPUT_DB   = "data.db"
MIN_MATCHES = 5   # minimum matches per team before we trust form stats


def load_csv(path=INPUT_FILE):
    rows = []
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            try:
                row["home_goals"] = int(row["home_goals"])
                row["away_goals"] = int(row["away_goals"])
                row["matchday"]   = int(row.get("matchday", 0))
                row["date_dt"]    = datetime.strptime(row["date"][:10], "%Y-%m-%d")
                rows.append(row)
            except Exception:
                continue
    rows.sort(key=lambda r: r["date_dt"])
    return rows


def build_features(rows):
    """
    For each match, compute rolling form features using only prior matches
    (no data leakage).
    """
    team_history = defaultdict(list)  # team -> list of past match dicts
    features = []

    for r in rows:
        home = r["home_team"]
        away = r["away_team"]

        hh = team_history[home]
        ah = team_history[away]

        def recent(history, n=5):
            return history[-n:] if len(history) >= n else history

        def form_pts(history):
            pts = 0
            for h in history:
                pts += h.get("pts", 0)
            return pts / max(len(history), 1)

        def goals_scored_avg(history):
            if not history:
                return 1.2
            return sum(h["gf"] for h in history) / len(history)

        def goals_conceded_avg(history):
            if not history:
                return 1.2
            return sum(h["ga"] for h in history) / len(history)

        def wins(history):
            return sum(1 for h in history if h["result"] == "W") / max(len(history), 1)

        def draws(history):
            return sum(1 for h in history if h["result"] == "D") / max(len(history), 1)

        home_recent = recent(hh)
        away_recent = recent(ah)

        feat = {
            # Rolling form (last 5 games)
            "home_form_pts":      form_pts(home_recent),
            "away_form_pts":      form_pts(away_recent),
            "home_goals_scored":  goals_scored_avg(home_recent),
            "home_goals_conceded":goals_conceded_avg(home_recent),
            "away_goals_scored":  goals_scored_avg(away_recent),
            "away_goals_conceded":goals_conceded_avg(away_recent),
            "home_win_rate":      wins(home_recent),
            "away_win_rate":      wins(away_recent),
            "home_draw_rate":     draws(home_recent),
            "away_draw_rate":     draws(away_recent),
            # Total history win rates (longer window)
            "home_overall_win":   wins(hh),
            "away_overall_win":   wins(ah),
            # Goal difference trend
            "home_gd_avg":        (goals_scored_avg(home_recent) - goals_conceded_avg(home_recent)),
            "away_gd_avg":        (goals_scored_avg(away_recent) - goals_conceded_avg(away_recent)),
            # Data confidence
            "home_match_count":   len(hh),
            "away_match_count":   len(ah),
            # Matchday / seasonality
            "matchday":           r["matchday"],
            "month":              r["date_dt"].month,
            "day_of_week":        r["date_dt"].weekday(),
            # Target
            "outcome":            r["outcome"],
            # Meta (not used as features)
            "date":               r["date"],
            "home_team":          home,
            "away_team":          away,
            "home_goals":         r["home_goals"],
            "away_goals":         r["away_goals"],
            "league":             r.get("league", ""),
        }
        features.append(feat)

        # Update histories after recording features (prevent leakage)
        hg, ag = r["home_goals"], r["away_goals"]
        home_result = "W" if hg > ag else ("L" if hg < ag else "D")
        away_result = "W" if ag > hg else ("L" if ag < hg else "D")
        home_pts = 3 if home_result == "W" else (1 if home_result == "D" else 0)
        away_pts = 3 if away_result == "W" else (1 if away_result == "D" else 0)

        team_history[home].append({"gf": hg, "ga": ag, "result": home_result, "pts": home_pts})
        team_history[away].append({"gf": ag, "ga": hg, "result": away_result, "pts": away_pts})

    # Keep only rows where both teams have enough history
    confident = [f for f in features if f["home_match_count"] >= MIN_MATCHES and f["away_match_count"] >= MIN_MATCHES]
    print(f"[OK] Total rows: {len(features)}, after confidence filter: {len(confident)}")
    return confident


def save_to_db(features, db_path=OUTPUT_DB):
    con = sqlite3.connect(db_path)
    cur = con.cursor()

    cur.execute("DROP TABLE IF EXISTS matches")
    cur.execute("""
        CREATE TABLE matches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT, league TEXT, home_team TEXT, away_team TEXT,
            home_goals INTEGER, away_goals INTEGER, outcome TEXT,
            home_form_pts REAL, away_form_pts REAL,
            home_goals_scored REAL, home_goals_conceded REAL,
            away_goals_scored REAL, away_goals_conceded REAL,
            home_win_rate REAL, away_win_rate REAL,
            home_draw_rate REAL, away_draw_rate REAL,
            home_overall_win REAL, away_overall_win REAL,
            home_gd_avg REAL, away_gd_avg REAL,
            home_match_count INTEGER, away_match_count INTEGER,
            matchday INTEGER, month INTEGER, day_of_week INTEGER
        )
    """)

    for f in features:
        cur.execute("""
            INSERT INTO matches (
                date, league, home_team, away_team, home_goals, away_goals, outcome,
                home_form_pts, away_form_pts,
                home_goals_scored, home_goals_conceded,
                away_goals_scored, away_goals_conceded,
                home_win_rate, away_win_rate,
                home_draw_rate, away_draw_rate,
                home_overall_win, away_overall_win,
                home_gd_avg, away_gd_avg,
                home_match_count, away_match_count,
                matchday, month, day_of_week
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            f["date"], f["league"], f["home_team"], f["away_team"],
            f["home_goals"], f["away_goals"], f["outcome"],
            f["home_form_pts"], f["away_form_pts"],
            f["home_goals_scored"], f["home_goals_conceded"],
            f["away_goals_scored"], f["away_goals_conceded"],
            f["home_win_rate"], f["away_win_rate"],
            f["home_draw_rate"], f["away_draw_rate"],
            f["home_overall_win"], f["away_overall_win"],
            f["home_gd_avg"], f["away_gd_avg"],
            f["home_match_count"], f["away_match_count"],
            f["matchday"], f["month"], f["day_of_week"],
        ))

    con.commit()
    con.close()
    print(f"[OK] Saved {len(features)} rows to {db_path}")


if __name__ == "__main__":
    if not os.path.exists(INPUT_FILE):
        print(f"[ERROR] {INPUT_FILE} not found. Run scraper.py first.")
    else:
        rows = load_csv(INPUT_FILE)
        features = build_features(rows)
        save_to_db(features)
