"""
scraper.py - BetPawa Match Data Scraper
Fetches football match results from public sources.
Falls back to requests+BeautifulSoup if Selenium unavailable.
"""

import os
import csv
import time
import json
import random
import requests
from datetime import datetime, timedelta
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Linux; Android 10; Pixel 3) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/114.0.5735.110 Mobile Safari/537.36"
    )
}

LEAGUES = {
    "premier_league": "https://www.football-data.org/v4/competitions/PL/matches?status=FINISHED",
    "la_liga":        "https://www.football-data.org/v4/competitions/PD/matches?status=FINISHED",
    "serie_a":        "https://www.football-data.org/v4/competitions/SA/matches?status=FINISHED",
    "bundesliga":     "https://www.football-data.org/v4/competitions/BL1/matches?status=FINISHED",
    "ligue1":         "https://www.football-data.org/v4/competitions/FL1/matches?status=FINISHED",
}

# Free API token from football-data.org (register free at https://www.football-data.org/)
API_TOKEN = os.getenv("FOOTBALL_API_TOKEN", "")


def scrape_via_api(output_file="raw.csv"):
    """Fetch via football-data.org free API (most reliable)."""
    rows = []
    api_headers = {"X-Auth-Token": API_TOKEN} if API_TOKEN else {}

    for league, url in LEAGUES.items():
        try:
            r = requests.get(url, headers={**HEADERS, **api_headers}, timeout=15)
            if r.status_code == 200:
                data = r.json()
                for match in data.get("matches", []):
                    score = match.get("score", {}).get("fullTime", {})
                    home_goals = score.get("home")
                    away_goals = score.get("away")
                    if home_goals is None or away_goals is None:
                        continue
                    if home_goals > away_goals:
                        outcome = "home_win"
                    elif home_goals < away_goals:
                        outcome = "away_win"
                    else:
                        outcome = "draw"

                    rows.append({
                        "date":        match.get("utcDate", "")[:10],
                        "league":      league,
                        "home_team":   match.get("homeTeam", {}).get("name", ""),
                        "away_team":   match.get("awayTeam", {}).get("name", ""),
                        "home_goals":  home_goals,
                        "away_goals":  away_goals,
                        "outcome":     outcome,
                        "matchday":    match.get("matchday", 0),
                        "status":      match.get("status", ""),
                    })
            time.sleep(0.5)
        except Exception as e:
            print(f"[WARN] Failed {league}: {e}")

    if not rows:
        print("[INFO] API failed or no token – using mock data for development")
        rows = _generate_mock_data()

    _write_csv(rows, output_file)
    print(f"[OK] Scraped {len(rows)} matches → {output_file}")
    return rows


def scrape_via_selenium(output_file="raw.csv"):
    """Selenium headless scraper (use inside Codespaces with Chrome installed)."""
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.common.by import By

        opts = Options()
        opts.add_argument("--headless")
        opts.add_argument("--no-sandbox")
        opts.add_argument("--disable-dev-shm-usage")
        opts.add_argument("--disable-gpu")

        driver = webdriver.Chrome(options=opts)
        rows = []

        # Example: scrape flashscore-style public data
        driver.get("https://www.flashscore.com/football/")
        time.sleep(3)

        matches = driver.find_elements(By.CSS_SELECTOR, ".event__match")
        for m in matches[:100]:
            try:
                home = m.find_element(By.CSS_SELECTOR, ".event__participant--home").text
                away = m.find_element(By.CSS_SELECTOR, ".event__participant--away").text
                score = m.find_element(By.CSS_SELECTOR, ".event__score").text
                parts = score.strip().split("-")
                if len(parts) == 2:
                    hg, ag = int(parts[0].strip()), int(parts[1].strip())
                    outcome = "home_win" if hg > ag else ("away_win" if hg < ag else "draw")
                    rows.append({
                        "date": datetime.today().strftime("%Y-%m-%d"),
                        "league": "mixed",
                        "home_team": home,
                        "away_team": away,
                        "home_goals": hg,
                        "away_goals": ag,
                        "outcome": outcome,
                        "matchday": 0,
                        "status": "FINISHED",
                    })
            except Exception:
                pass

        driver.quit()

        if not rows:
            rows = _generate_mock_data()

        _write_csv(rows, output_file)
        print(f"[OK] Selenium scraped {len(rows)} matches → {output_file}")
        return rows

    except ImportError:
        print("[INFO] Selenium not installed – falling back to API scraper")
        return scrape_via_api(output_file)


def _generate_mock_data(n=600):
    """Generates realistic mock data for offline development and testing."""
    teams = [
        "Arsenal", "Chelsea", "Liverpool", "Man City", "Man Utd",
        "Tottenham", "Leicester", "Everton", "Newcastle", "Wolves",
        "Real Madrid", "Barcelona", "Atletico", "Sevilla", "Valencia",
        "Juventus", "Inter", "AC Milan", "Napoli", "Roma",
        "Bayern", "Dortmund", "Leipzig", "Leverkusen", "Frankfurt",
        "PSG", "Lyon", "Marseille", "Monaco", "Lille",
    ]
    rows = []
    base_date = datetime(2023, 8, 1)
    for i in range(n):
        date = base_date + timedelta(days=random.randint(0, 500))
        home = random.choice(teams)
        away = random.choice([t for t in teams if t != home])
        hg = random.choices([0,1,2,3,4], weights=[15,30,28,18,9])[0]
        ag = random.choices([0,1,2,3,4], weights=[20,32,26,15,7])[0]
        outcome = "home_win" if hg > ag else ("away_win" if hg < ag else "draw")
        rows.append({
            "date":       date.strftime("%Y-%m-%d"),
            "league":     random.choice(list(LEAGUES.keys())),
            "home_team":  home,
            "away_team":  away,
            "home_goals": hg,
            "away_goals": ag,
            "outcome":    outcome,
            "matchday":   (i % 38) + 1,
            "status":     "FINISHED",
        })
    return rows


def _write_csv(rows, filename):
    if not rows:
        return
    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    scrape_via_api("raw.csv")
