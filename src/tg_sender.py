from typing import Optional
from telegram import Bot
from src.config import TG_BOT_TOKEN, TG_CHAT_ID

_bot = Bot(token=TG_BOT_TOKEN)

def send_message(text: str, parse_mode: Optional[str] = None):
    _bot.send_message(
        chat_id=TG_CHAT_ID,
        text=text,
        parse_mode=parse_mode
    )

def send_photo(photo_path: str, caption: str = ""):
    bot = Bot(token=TG_BOT_TOKEN)
    with open(photo_path, "rb") as f:
        bot.send_photo(chat_id=TG_CHAT_ID, photo=f, caption=caption)
