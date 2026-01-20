#!/usr/bin/env bash
set -euo pipefail

cd /Users/pivan/siteandbot/ozon_analysis_bot

mkdir -p logs

source .venv/bin/activate

python -m src.main >> logs/ozon_analysis_bot.log 2>&1
