
import io
import math

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.patches import Rectangle


def make_signal_chart(candles, ind, strategy, side, entry, sl, tp):
    if not candles:
        raise ValueError("Candles cannot be empty")

    required = (
        "fast",
        "slow",
        "pullback",
        "ema21",
        "ema50",
        "adx",
        "plus_di",
        "minus_di",
    )

    missing = [key for key in required if key not in ind]
    if missing:
        raise ValueError(
            f"Missing indicators for chart: {missing}"
        )

    subset = candles[-70:]
    offset = len(candles) - len(subset)

    times = [
        mdates.date2num(c["time"])
        for c in subset
    ]

    fig, (ax_price, ax_adx) = plt.subplots(
        2,
        1,
        figsize=(12, 8),
        sharex=True,
        gridspec_kw={"height_ratios": [3, 1]},
    )

    # ==================================
    # PRICE CHART
    # ==================================

    for x, candle in zip(times, subset):
        color = (
            "#16a34a"
            if candle["close"] >= candle["open"]
            else "#dc2626"
        )

        ax_price.vlines(
            x,
            candle["low"],
            candle["high"],
            color=color,
            linewidth=1,
        )

        body = max(
            abs(candle["close"] - candle["open"]),
            0.001,
        )

        ax_price.add_patch(
            Rectangle(
                (
                    x - 0.006,
                    min(candle["open"], candle["close"]),
                ),
                0.012,
                body,
                facecolor=color,
                edgecolor=color,
            )
        )

    # PEMA approximation
    ax_price.plot(
        times,
        ind["fast"][offset:],
        label="Fast PEMA proxy 1",
        color="#06b6d4",
    )

    ax_price.plot(
        times,
        ind["slow"][offset:],
        label="Slow PEMA proxy 3",
        color="#f59e0b",
    )

    # Quality Edition trend indicators
    ax_price.plot(
        times,
        ind["pullback"][offset:],
        label="EMA13 Pullback",
        color="#a855f7",
    )

    ax_price.plot(
        times,
        ind["ema21"][offset:],
        label="EMA21 Trend",
        color="#2563eb",
        linewidth=1.5,
    )

    ax_price.plot(
        times,
        ind["ema50"][offset:],
        label="EMA50 Trend",
        color="#ec4899",
        linewidth=1.5,
    )

    # Entry, Stop Loss and Take Profit
    ax_price.axhline(
        entry,
        color="#2563eb",
        linestyle="--",
        label=f"ENTRY {entry:.3f}",
    )

    ax_price.axhline(
        sl,
        color="#dc2626",
        linestyle="--",
        label=f"SL {sl:.3f}",
    )

    ax_price.axhline(
        tp,
        color="#16a34a",
        linestyle="--",
        label=f"TP {tp:.3f}",
    )

    ax_price.set_title(
        f"XAUUSD M30 | {strategy} | {side}",
        fontsize=14,
        weight="bold",
    )

    ax_price.set_ylabel("Price")
    ax_price.grid(alpha=0.2)
    ax_price.legend(
        loc="upper left",
        fontsize=8,
    )

    # ==================================
    # ADX / DIRECTIONAL INDICATORS
    # ==================================

    def chart_values(key):
        return [
            float("nan") if value is None else value
            for value in ind[key][offset:]
        ]

    ax_adx.plot(
        times,
        chart_values("adx"),
        label="ADX 14",
        color="#2563eb",
        linewidth=1.5,
    )

    ax_adx.plot(
        times,
        chart_values("plus_di"),
        label="+DI",
        color="#16a34a",
    )

    ax_adx.plot(
        times,
        chart_values("minus_di"),
        label="-DI",
        color="#dc2626",
    )

    ax_adx.axhline(
        20,
        color="#f59e0b",
        linestyle="--",
        label="ADX Threshold 20",
    )

    ax_adx.set_ylim(0, 100)
    ax_adx.set_ylabel("ADX / DI")
    ax_adx.set_xlabel("Time (UTC)")
    ax_adx.grid(alpha=0.2)
    ax_adx.legend(
        loc="upper left",
        fontsize=8,
        ncol=2,
    )

    ax_adx.xaxis.set_major_formatter(
        mdates.DateFormatter(
            "%d %b %H:%M",
            tz=times_timezone(),
        )
    )

    fig.autofmt_xdate()
    fig.tight_layout()

    output = io.BytesIO()

    fig.savefig(
        output,
        format="png",
        dpi=140,
    )

    plt.close(fig)
    output.seek(0)

    return output


def times_timezone():
    from datetime import timezone
    return timezone.utc
