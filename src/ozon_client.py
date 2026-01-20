# src/ozon_client.py
import os
import requests
from datetime import date, timedelta
from dotenv import load_dotenv
from pathlib import Path

BASE = "https://api-seller.ozon.ru"

def _load_env():
    # чтобы работало одинаково и локально и на сервере
    env_path = Path(__file__).resolve().parent.parent / ".env"
    load_dotenv(dotenv_path=env_path)

def fetch_ozon_14d():
    _load_env()

    client_id = os.getenv("OZON_CLIENT_ID")
    api_key = os.getenv("OZON_API_KEY")
    if not client_id or not api_key:
        raise RuntimeError("Нет OZON_CLIENT_ID / OZON_API_KEY в .env")

    d_to = date.today() - timedelta(days=1)      # вчера
    d_from = d_to - timedelta(days=13)           # 14 дней

    url = f"{BASE}/v1/analytics/data"
    payload = {
        "date_from": d_from.isoformat(),
        "date_to": d_to.isoformat(),
        "metrics": ["revenue", "ordered_units"],
        "dimension": ["day"],
        "filters": [],
        "sort": [{"key": "day", "order": "ASC"}],
        "limit": 1000,
        "offset": 0
    }
    headers = {
        "Client-Id": str(client_id),
        "Api-Key": api_key,
        "Content-Type": "application/json"
    }

    r = requests.post(url, json=payload, headers=headers, timeout=30)
    r.raise_for_status()
    js = r.json()

    out = []
    for row in js["result"]["data"]:
        day = row["dimensions"][0]["id"]          # "YYYY-MM-DD"
        revenue = float(row["metrics"][0] or 0)   # revenue
        units = int(row["metrics"][1] or 0)       # ordered_units
        out.append((day, revenue, units))

    return out
