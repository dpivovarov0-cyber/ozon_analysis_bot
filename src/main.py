from datetime import date, timedelta
from src.ozon_client import fetch_ozon_14d
from src.tg_sender import send_message
from src.report import make_ozon_charts_14d
from src.tg_sender import send_photo
from datetime import date, timedelta
from src.logger import setup_logger
from src.ads_client import fetch_ads_spend_by_day


def fmt_int(n: int) -> str:
    return f"{n:,}".replace(",", " ")

def fmt_money(rub: float) -> str:
    return f"{int(round(rub)):,}".replace(",", " ") + " ₽"

def fmt_delta(cur: float, prev: float, money=False):
    d = cur - prev
    pct = (d / prev * 100.0) if prev else 0.0
    if money:
        return f"({d:+.0f} ₽ | {pct:+.1f}%)"
    else:
        return f"({d:+.0f} | {pct:+.1f}%)"

def trend_icon(cur: float, prev: float) -> str:
    if prev is None:
        return "•"
    if cur > prev:
        return "▲"
    if cur < prev:
        return "▼"
    return "•"

def main():
    setup_logger()
    days = fetch_ozon_14d()  # [(YYYY-MM-DD, revenue, units), ...] ASC

    # --- реклама OZON (затраты по дням) ---
    date_from = date.fromisoformat(days[0][0])
    date_to = date.fromisoformat(days[-1][0])

    try:
        ads_by_day = fetch_ads_spend_by_day(date_from, date_to)
    except Exception as e:
        # если реклама не получилась — не ломаем отчёт
        import logging
        logging.getLogger("ozon_ads").exception("ADS fetch failed")
        ads_by_day = {}

    if len(days) < 2:
        send_message("OZON: мало данных для отчёта")
        return

    # --- вчера / позавчера по продажам ---
    y_day, y_rev, y_units = days[-1]
    p_day, p_rev, p_units = days[-2]

    # --- реклама OZON ---
    y_ads = float(ads_by_day.get(y_day, 0.0))
    p_ads = float(ads_by_day.get(p_day, 0.0))

    y_cpo = (y_ads / y_units) if y_units else 0.0
    p_cpo = (p_ads / p_units) if p_units else 0.0

    aov_y = (y_rev / y_units) if y_units else 0.0
    aov_p = (p_rev / p_units) if p_units else 0.0

    text = (
        f"*Отчет за {y_day} (вчера)*\n\n"
        f"*OZON*\n"
        f"*Штуки:* *{fmt_int(y_units)}* {trend_icon(y_units, p_units)} {fmt_delta(y_units, p_units)}\n"
        f"Средний чек: {fmt_money(aov_y)} {trend_icon(aov_y, aov_p)} ({aov_y - aov_p:+.0f} ₽)\n"
        f"Реклама: {fmt_money(y_ads)} {trend_icon(y_ads, p_ads)} {fmt_delta(y_ads, p_ads, money=True)}\n"
        f"CPO: {y_cpo:.1f} ₽ {trend_icon(y_cpo, p_cpo)} ({y_cpo - p_cpo:+.1f} ₽)"
    )

    # ВАЖНО: чтобы звёздочки стали жирным — нужен parse_mode
    send_message(text, parse_mode="Markdown")

    from src.report import make_ozon_charts_14d
    from src.tg_sender import send_photo

    charts = make_ozon_charts_14d(ads_by_day=ads_by_day)
    for p in charts:
        send_photo(str(p))

if __name__ == "__main__":
    main()
