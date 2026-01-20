from pathlib import Path
from typing import List
import matplotlib.pyplot as plt
from matplotlib.ticker import MultipleLocator

from src.ozon_client import fetch_ozon_14d

OUT_DIR = Path("out/charts")


def _nice_step(max_val: float) -> int:
    if max_val <= 0:
        return 1
    for step in [1, 5, 10, 50, 100, 500, 1000, 5000, 10000]:
        if max_val / step <= 10:
            return step
    return 20000


def make_ozon_charts_14d(ads_by_day=None) -> List[Path]:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUT_DIR / "ozon_14d.png"

    days = fetch_ozon_14d()
    if not days:
        return [out_path]

    dates = [d[0][5:] for d in days]  # подписи оси X
    x = list(range(len(dates)))  # реальные X-координаты (числа)

    revenue = [float(d[1]) for d in days]
    units = [int(d[2]) for d in days]
    avg_check = [(revenue[i] / units[i]) if units[i] else 0 for i in range(len(units))]

    ads_by_day = ads_by_day or {}
    day_keys = [d[0] for d in days]  # YYYY-MM-DD
    ads_spend = [float(ads_by_day.get(k, 0.0)) for k in day_keys]
    cpo = [(ads_spend[i] / units[i]) if units[i] else 0.0 for i in range(len(units))]

    fig, (ax_top, ax_bottom) = plt.subplots(
        2, 1, figsize=(10.8, 6.0),
        gridspec_kw={"height_ratios": [3, 2]},
        sharex=True
    )
    fig.suptitle("OZON — 14 дней")

    # ===== TOP: Средний чек + Штуки =====
    bars = ax_top.bar(x, avg_check, alpha=0.3, label="Средний чек")
    ax_top.set_ylabel("Средний чек (₽)")
    ax_top.set_ylim(500, 1000)
    ax_top.yaxis.set_major_locator(MultipleLocator(100))

    ax_units = ax_top.twinx()
    ax_units.plot(x, units, marker="o", linewidth=2.5, label="Штуки")
    ax_units.set_ylabel("Штуки")
    ax_units.set_ylim(0, 500)
    ax_units.yaxis.set_major_locator(MultipleLocator(50))  # <-- было 100

    # подпись последнего значения "Штуки"
    x_last = x[-1]
    y_last = units[-1]
    ax_units.annotate(
        f"{y_last}",
        xy=(x_last, y_last),
        xytext=(0, 9),
        textcoords="offset points",
        ha="center",
        va="center",
        fontsize=9,
        fontweight="bold"
    )

    ax_top.legend(loc="upper left")
    ax_units.legend(loc="upper right")
    ax_top.grid(axis="y", alpha=0.15)

    # ===== BOTTOM: Реклама + CPO (как WB: столбики) =====
    ax_bottom.set_ylabel("Реклама (₽)")
    ax_bottom.set_ylim(0, 20000)
    ax_bottom.yaxis.set_major_locator(MultipleLocator(5000))
    ax_bottom.grid(axis="y", alpha=0.15)

    # широкие столбики расходов (голубые)
    bars_spend = ax_bottom.bar(
        x, ads_spend,
        alpha=1.0,
        label="Реклама (₽)",
        color="#b9d4e6"
    )

    # подписи расходов сверху (как в WB)
    for i, b in enumerate(bars_spend):
        v = ads_spend[i]
        if v > 0:
            ax_bottom.text(
                b.get_x() + b.get_width() / 2,
                b.get_height() * 0.85,
                f"{int(round(v)):,}".replace(",", " "),
                ha="center",
                va="bottom",
                fontsize=8,
                fontweight="bold"
            )

    # правая ось для CPO
    ax_cpo = ax_bottom.twinx()
    ax_cpo.set_ylabel("CPO (₽/шт)")
    ax_cpo.set_ylim(20, 80)
    ax_cpo.yaxis.set_major_locator(MultipleLocator(10))

    # узкие жёлтые столбики CPO "внутри" (поверх расходов)
    bars_cpo = ax_cpo.bar(
        x, cpo,
        width=0.35,
        alpha=0.95,
        label="CPO (₽/шт)",
        color="#f3c74a",
        zorder=3
    )

    # подписи CPO внутри жёлтых столбиков
    for i, b in enumerate(bars_cpo):
        v = cpo[i]
        if v > 0:
            ax_cpo.text(
                b.get_x() + b.get_width() / 2,
                b.get_height() * 0.95,
                f"{v:.1f}",
                ha="center",
                va="center",
                fontsize=7,
                fontweight="bold",
                color="white",
                zorder=4
            )

    ax_bottom.legend(loc="upper left")
    ax_cpo.legend(loc="upper right")

    # ✅ ВОТ ЭТО ВАЖНО: возвращаем подписи дат
    ax_bottom.set_xticks(x)
    ax_bottom.set_xticklabels(dates)

    fig.tight_layout()
    fig.savefig(out_path, dpi=180)
    plt.close(fig)

    return [out_path]
