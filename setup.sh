#!/bin/bash
# setup.sh - Full pipeline runner
# Run inside Codespaces or locally after cloning the repo

set -e
echo "=== BetPawa Predictor Setup ==="

echo "[1/4] Scraping match data..."
python scraper.py

echo "[2/4] Cleaning data & engineering features..."
python clean.py

echo "[3/4] Training XGBoost model..."
python train.py

echo "[4/4] All done! Launch the app with:"
echo "       python main.py"
echo ""
echo "To build APK locally:"
echo "       buildozer android debug"
echo ""
echo "To build APK via GitHub Actions:"
echo "       git add . && git commit -m 'trigger build' && git push"
echo "       Then check: https://github.com/Sharif123-cloud/betpawa-predictor/releases"
