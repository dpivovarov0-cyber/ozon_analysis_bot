# src/logger.py
from pathlib import Path
import logging

def setup_logger() -> None:
    Path("logs").mkdir(exist_ok=True)
    log_path = Path("logs/ozon_analysis_bot.log")

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        handlers=[
            logging.FileHandler(log_path, encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )
