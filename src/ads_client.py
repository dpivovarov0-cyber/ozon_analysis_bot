from __future__ import annotations

from datetime import date
import os
import logging
from pathlib import Path
from typing import Any, Dict, Optional

import csv
import io

import requests
from dotenv import load_dotenv

log = logging.getLogger("ozon_ads")

BASE_URL_CANDIDATES = [
    "https://api-performance.ozon.ru/api/client",  # самый частый вариант
    "https://performance.ozon.ru/api/client",
    "https://performance.ozon.ru/api",
    "https://api-performance.ozon.ru/api",
]


def _load_env() -> None:
    # Чтобы одинаково работало локально и на сервере/cron
    env_path = Path(__file__).resolve().parent.parent / ".env"
    load_dotenv(dotenv_path=env_path)


def _safe_json(resp: requests.Response, context: str) -> Optional[Dict[str, Any]]:
    """
    Пытаемся распарсить JSON и даём нормальный лог,
    если тело пустое или пришёл HTML/редирект.
    """
    if not resp.content or len(resp.content) == 0:
        log.error("ADS: пустой ответ (%s): status=%s", context, resp.status_code)
        return None

    ctype = (resp.headers.get("Content-Type") or "").lower()
    text_preview = (resp.text or "").strip()[:400]

    try:
        return resp.json()
    except Exception:
        log.error(
            "ADS: не JSON (%s): status=%s, content-type=%s, body[0:400]=%r",
            context,
            resp.status_code,
            ctype,
            text_preview,
        )
        return None


def _parse_csv_spend_by_day(text: str) -> Dict[str, float]:
    """
    CSV формата:
    ID;Название;Дата;Показы;Клики;Расход, ₽;Заказы, шт.;Заказы, ₽
    ...
    Возвращает { 'YYYY-MM-DD': spend_float }
    """
    out: Dict[str, float] = {}

    # иногда бывает BOM в начале
    cleaned = text.lstrip("\ufeff").strip()
    if not cleaned:
        return out

    reader = csv.DictReader(io.StringIO(cleaned), delimiter=";")
    for row in reader:
        day = (row.get("Дата") or row.get("date") or row.get("day") or "").strip()
        spend_raw = (row.get("Расход, ₽") or row.get("spend") or row.get("cost") or "0").strip()

        # "990,79" -> 990.79
        spend_raw = spend_raw.replace(" ", "").replace("\xa0", "")
        spend_raw = spend_raw.replace(",", ".")
        try:
            spend = float(spend_raw) if spend_raw else 0.0
        except ValueError:
            spend = 0.0

        if day:
            out[day] = out.get(day, 0.0) + spend

    return out

def _get_access_token() -> Optional[str]:
    _load_env()

    client_id = os.getenv("OZON_PERF_CLIENT_ID", "").strip()
    client_secret = os.getenv("OZON_PERF_CLIENT_SECRET", "").strip()

    if not client_id or not client_secret:
        log.error("ADS: нет OZON_PERF_CLIENT_ID / OZON_PERF_CLIENT_SECRET в .env")
        return None

    payload = {
        "client_id": client_id,
        "client_secret": client_secret,
        "grant_type": "client_credentials",
    }
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
    }

    last_err = None

    for base in BASE_URL_CANDIDATES:
        url = f"{base}/token"
        try:
            r = requests.post(url, json=payload, headers=headers, timeout=20)

            if r.status_code != 200:
                # логируем кратко, чтобы видеть какой base живой
                body = (r.text or "")[:200].replace("\n", " ")
                log.error("ADS: token %s -> %s: %s", url, r.status_code, body)
                last_err = (r.status_code, body)
                continue

            js = _safe_json(r, f"token ({base})") or {}
            token = js.get("access_token")
            if token:
                # сохраним выбранный base в переменную окружения на время процесса
                os.environ["OZON_PERF_BASE_URL"] = base
                log.info("ADS: token OK, base=%s", base)
                return token

            log.error("ADS: token OK, но access_token отсутствует, base=%s", base)
            last_err = ("no_access_token", str(js)[:200])

        except Exception as e:
            log.exception("ADS: token exception для %s", url)
            last_err = ("exception", str(e))

    log.error("ADS: не удалось получить token ни с одного base. last=%r", last_err)
    return None



def fetch_ads_spend_by_day(date_from: date, date_to: date) -> Dict[str, float]:
    """
    Возвращает:
    {
      '2026-01-18': 123.45,
      '2026-01-19': 67.89,
      ...
    }
    """
    try:
        token = _get_access_token()
        if not token:
            return {}

        base = os.getenv("OZON_PERF_BASE_URL") or BASE_URL_CANDIDATES[0]

        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
        }

        # 1. Получаем список кампаний
        res_c = requests.get(
            f"{base}/campaign",
            headers=headers,
            timeout=20,
        )

        if res_c.status_code != 200:
            log.error(
                "ADS: campaign ошибка %s: %s",
                res_c.status_code,
                (res_c.text or "")[:400],
            )
            return {}

        js_c = _safe_json(res_c, "campaign") or {}
        campaigns = js_c.get("list") or js_c.get("result") or []

        # Берём RUNNING, если есть — иначе любые
        running = [
            c for c in campaigns
            if c.get("state") == "CAMPAIGN_STATE_RUNNING"
        ]
        picked = running if running else campaigns

        # Ограничим количество id (часто есть лимиты)
        campaign_ids = [
            str(c.get("id"))
            for c in picked
            if c.get("id") is not None
        ][:10]

        if not campaign_ids:
            log.info("ADS: кампаний не найдено")
            return {}

        # ВАЖНО: campaign_ids повторяющимися параметрами
        params = [("campaign_ids", int(cid)) for cid in campaign_ids]
        params += [
            ("date_from", date_from.isoformat()),
            ("date_to", date_to.isoformat()),
        ]

        res = requests.get(
            f"{base}/statistics/campaign/daily",
            params=params,
            headers=headers,
            timeout=30,
        )

        # fallback на общий эндпоинт
        if res.status_code != 200:
            log.info("ADS: Попытка через общий эндпоинт статистики...")
            res = requests.get(
                f"{base}/statistics/daily",
                params=params,
                headers=headers,
                timeout=30,
            )

        if res.status_code != 200:
            log.error(
                "ADS: ошибка статистики %s: %s",
                res.status_code,
                (res.text or "")[:400],
            )
            return {}

        ctype = (res.headers.get("Content-Type") or "").lower()

        # ✅ если пришёл CSV — парсим CSV и возвращаем результат
        if "text/csv" in ctype or "application/csv" in ctype:
            out = _parse_csv_spend_by_day(res.text or "")
            log.info("ADS: CSV статистика, получено %s дней", len(out))
            return out

        # иначе пытаемся как JSON (на будущее)
        data = _safe_json(res, "stats")
        if not data:
            return {}

        # дальше твой JSON-парсинг rows -> out (как у тебя уже сделано)

        # Поддержка разных форматов ответа
        rows = []
        if isinstance(data.get("result"), list):
            rows = data.get("result", [])
        elif isinstance(data.get("rows"), list):
            rows = data.get("rows", [])
        elif isinstance(data.get("result"), dict) and isinstance(data["result"].get("rows"), list):
            rows = data["result"]["rows"]

        out: Dict[str, float] = {}

        for row in rows:
            day = row.get("date") or row.get("day")
            spend = (
                row.get("spend")
                or row.get("money")
                or row.get("cost")
                or 0
            )

            if day:
                out[str(day)] = out.get(str(day), 0.0) + float(spend)

        log.info("ADS: Успешно получено %s дней", len(out))
        return out

    except Exception:
        log.exception("ADS: Сбой")
        return {}
