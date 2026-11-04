import io
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.patches import Rectangle


def make_signal_chart(candles, ind, strategy, side, entry, sl, tp):
    subset = candles[-70:]
    offset = len(candles) - len(subset)
    times = [mdates.date2num(c["time"]) for c in subset]

    fig, ax = plt.subplots(figsize=(12, 7))
    for x, c in zip(times, subset):
        color = "#16a34a" if c["close"] >= c["open"] else "#dc2626"
        ax.vlines(x, c["low"], c["high"], color=color, linewidth=1)
        body = max(abs(c["close"] - c["open"]), 0.001)
        ax.add_patch(Rectangle(
            (x - 0.006, min(c["open"], c["close"])), 0.012, body,
            facecolor=color, edgecolor=color
        ))

    ax.plot(times, ind["fast"][offset:], label="Fast PEMA proxy 1", color="#06b6d4")
    ax.plot(times, ind["slow"][offset:], label="Slow PEMA proxy 3", color="#f59e0b")
    ax.plot(times, ind["trend"][offset:], label="Trend PEMA proxy 21", color="#2563eb", linewidth=1.5)
    ax.plot(times, ind["pullback"][offset:], label="EMA13 pullback", color="#a855f7")

    ax.axhline(entry, color="#2563eb", linestyle="--", label=f"ENTRY {entry:.3f}")
    ax.axhline(sl, color="#dc2626", linestyle="--", label=f"SL {sl:.3f}")
    ax.axhline(tp, color="#16a34a", linestyle="--", label=f"TP {tp:.3f}")

    ax.set_title(f"XAUUSD M30 | {strategy} | {side}", fontsize=14, weight="bold")
    ax.set_ylabel("Price")
    ax.xaxis_date()
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%d %b %H:%M", tz=times_timezone()))
    ax.grid(alpha=0.2)
    ax.legend(loc="upper left", fontsize=8)
    fig.autofmt_xdate()
    fig.tight_layout()

    output = io.BytesIO()
    fig.savefig(output, format="png", dpi=140)
    plt.close(fig)
    output.seek(0)
    return output


def times_timezone():
    from datetime import timezone
    return timezone.utc
