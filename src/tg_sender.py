import os
import logging
import requests
from dotenv import load_dotenv
from typing import Optional


log = logging.getLogger("tg_sender")

API = "https://api.telegram.org"


def _load_env():
    # грузим .env гарантированно при каждом вызове
    load_dotenv()


def _get_creds():
    _load_env()
    token = os.getenv("TG_BOT_TOKEN")
    chat_id = os.getenv("TG_CHAT_ID")
    if not token or not chat_id:
        raise RuntimeError("Нет TG_BOT_TOKEN или TG_CHAT_ID в .env")
    return token, chat_id


def send_message(text: str, parse_mode: str = "Markdown"):
    token, chat_id = _get_creds()
    url = f"{API}/bot{token}/sendMessage"
    data = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": parse_mode,
    }
    r = requests.post(url, data=data, timeout=30)
    if r.status_code != 200:
        raise RuntimeError(f"Telegram sendMessage error {r.status_code}: {r.text[:400]}")
    return r.json()


def send_photo(photo_path: str, caption: Optional[str] = None, parse_mode: str = "Markdown"):
    token, chat_id = _get_creds()
    url = f"{API}/bot{token}/sendPhoto"
    with open(photo_path, "rb") as f:
        files = {"photo": f}
        data = {"chat_id": chat_id}
        if caption:
            data["caption"] = caption
            data["parse_mode"] = parse_mode
        r = requests.post(url, data=data, files=files, timeout=60)
    if r.status_code != 200:
        raise RuntimeError(f"Telegram sendPhoto error {r.status_code}: {r.text[:400]}")
    return r.json()

