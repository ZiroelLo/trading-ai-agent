import os
import sys
import argparse
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from data_provider import get_closed_candles
from strategy import calculate_indicators, detect_signals
from chart import make_signal_chart
from database import (
    init_db, insert_signal, get_open_positions, update_position,
    get_period_stats, get_period_positions, get_last_report, save_report
)
from telegram_bot import send_message, send_photo

WIB = ZoneInfo("Asia/Jakarta")
NEW_YORK = ZoneInfo("America/New_York")
UTC = timezone.utc


def is_forex_market_open():
    now = datetime.now(NEW_YORK)
    weekday = now.weekday()

    # Sabtu: pasar tutup
    if weekday == 5:
        return False

    # Jumat pukul 17.00 ke atas: pasar tutup
    if weekday == 4 and now.hour >= 17:
        return False

    # Minggu sebelum pukul 17.00: pasar tutup
    if weekday == 6 and now.hour < 17:
        return False

    return True


def fmt_price(value):
    return f"{value:.3f}"


def track_open_positions(candles):
    """Evaluate every newly closed M30 candle for open positions."""
    if not candles:
        return

    for pos in get_open_positions():
        last_checked = (
            pos.get("last_checked_candle")
            or pos["candle_time"]
        )

        new_candles = [
            c for c in candles
            if c["time"] > pos["candle_time"]
            and c["time"] > last_checked
        ]

        for candle in new_candles:
            candle_time = candle["time"]

            if pos["side"] == "BUY":
                hit_sl = candle["low"] <= pos["stop_loss"]
                hit_tp = candle["high"] >= pos["take_profit"]
            else:
                hit_sl = candle["high"] >= pos["stop_loss"]
                hit_tp = candle["low"] <= pos["take_profit"]

            # If both levels are hit, count SL first.
            if hit_sl:
                update_position(
                    pos["id"], "SL", candle_time,
                    pos["stop_loss"], candle_time, pos["id"]
                )
                send_message(
                    f"🔴 XAUUSD POSITION CLOSED — SL\n"
                    f"Strategi: {pos['strategy']}\n"
                    f"Arah: {pos['side']}\n"
                    f"Entry: {fmt_price(pos['entry'])}\n"
                    f"Exit: {fmt_price(pos['stop_loss'])}\n"
                    f"Hasil: -1R\n"
                    f"Candle: {candle_time:%Y-%m-%d %H:%M} UTC"
                )
                break

            elif hit_tp:
                update_position(
                    pos["id"], "TP", candle_time,
                    pos["take_profit"], candle_time, pos["id"]
                )
                send_message(
                    f"🟢 XAUUSD POSITION CLOSED — TP\n"
                    f"Strategi: {pos['strategy']}\n"
                    f"Arah: {pos['side']}\n"
                    f"Entry: {fmt_price(pos['entry'])}\n"
                    f"Exit: {fmt_price(pos['take_profit'])}\n"
                    f"Hasil: +{pos['target_rr']:.1f}R\n"
                    f"Candle: {candle_time:%Y-%m-%d %H:%M} UTC"
                )
                break

            else:
                update_position(
                    pos["id"], "OPEN", None, None,
                    candle_time, pos["id"]
                )
                last_checked = candle_time

def run_scan():
    if not is_forex_market_open():
        print("Forex market closed — scanner skipped.")
        return

    init_db()
    candles = get_closed_candles()
    indicators = calculate_indicators(candles)

    # Update previously opened virtual positions first.
    track_open_positions(candles)

    signals = detect_signals(candles, indicators)
    candle = candles[-1]
    entry = candle["close"]
    atr = indicators["atr"][-1]

    print(f"Closed M30 candle: {candle['time']} | close={entry} | ATR={atr}")
    if not signals:
        print("No PEMA signal.")
        return

    for strategy_name, side in signals:
        risk = atr * 1.5
        if side == "BUY":
            stop_loss = entry - risk
            take_profit = entry + risk * 2.0
        else:
            stop_loss = entry + risk
            take_profit = entry - risk * 2.0

        signal_id = insert_signal(
            strategy_name, side, candle["time"], entry,
            stop_loss, take_profit, atr, 2.0
        )
        if signal_id is None:
            print(f"Duplicate ignored: {strategy_name} {side} {candle['time']}")
            continue

        chart = make_signal_chart(candles, indicators, strategy_name,
                                  side, entry, stop_loss, take_profit)
        caption = (
            f"📊 XAUUSD PEMA SIGNAL\n"
            f"Strategi: {strategy_name}\nArah: {side}\nTimeframe: M30\n\n"
            f"Entry: {fmt_price(entry)}\n"
            f"Stop Loss: {fmt_price(stop_loss)}\n"
            f"Take Profit: {fmt_price(take_profit)}\n"
            f"Risk/Reward: 1:2\nATR(14): {fmt_price(atr)}\n"
            f"Candle: {candle['time']:%Y-%m-%d %H:%M} UTC\n\n"
            "Sinyal simulasi/paper trading. Bukan instruksi atau jaminan profit."
        )
        send_photo(chart, caption)
        print(f"Sent: {strategy_name} {side}")


def report_text(kind, start_utc, end_utc):
    stats = get_period_stats(start_utc, end_utc)
    positions = get_period_positions(start_utc, end_utc)
    total = stats["total"]
    closed = stats["tp"] + stats["sl"]
    win_rate = (stats["tp"] / closed * 100) if closed else 0.0
    net_r = stats["tp_r"] - stats["sl"]

    lines = [
        f"📈 XAUUSD PEMA — {kind.upper()} REPORT",
        f"Periode: {start_utc.astimezone(WIB):%d/%m/%Y %H:%M} WIB – "
        f"{end_utc.astimezone(WIB):%d/%m/%Y %H:%M} WIB",
        "",
        f"Total sinyal: {total}",
        f"TP: {stats['tp']} | SL: {stats['sl']} | OPEN: {stats['open']}",
        f"Win rate (posisi selesai): {win_rate:.1f}%",
        f"Hasil terealisasi: {net_r:+.2f}R",
        "",
        "PER STRATEGI:"
    ]

    for strategy_name in ("Modified Crossover", "Pullback EMA13"):
        s = get_period_stats(start_utc, end_utc, strategy_name)
        done = s["tp"] + s["sl"]
        wr = (s["tp"] / done * 100) if done else 0.0
        r = s["tp_r"] - s["sl"]
        lines.append(
            f"• {strategy_name}: {s['total']} sinyal | "
            f"TP {s['tp']} | SL {s['sl']} | OPEN {s['open']} | "
            f"WR {wr:.1f}% | {r:+.2f}R"
        )

    lines += ["", "POSISI OPEN:"]
    open_items = [p for p in positions if p["status"] == "OPEN"]
    if open_items:
        for p in open_items[:15]:
            lines.append(
                f"• {p['strategy']} {p['side']} | Entry {p['entry']:.3f} | "
                f"SL {p['stop_loss']:.3f} | TP {p['take_profit']:.3f}"
            )
    else:
        lines.append("Tidak ada posisi terbuka.")

    lines += [
        "",
        "Catatan: statistik ini berdasarkan paper tracking dari data candle. "
        "Spread, slippage, komisi, dan urutan harga intrabar tidak sepenuhnya tercermin."
    ]
    return "\n".join(lines)


def run_weekly():
    init_db()
    now = datetime.now(UTC)
    # Previous Monday 00:00 WIB through Sunday 20:00 WIB.
    local_now = now.astimezone(WIB)
    end_local = local_now.replace(hour=20, minute=0, second=0, microsecond=0)
    start_local = (end_local - timedelta(days=6)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    start_utc, end_utc = start_local.astimezone(UTC), end_local.astimezone(UTC)
    key = f"weekly:{start_local.date()}"
    if get_last_report(key):
        print("Weekly report already sent.")
        return
    send_message(report_text("Weekly", start_utc, end_utc))
    save_report(key)


def run_monthly():
    init_db()
    now_local = datetime.now(UTC).astimezone(WIB)
    first_this_month = now_local.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    end_local = first_this_month
    previous_month_end = first_this_month - timedelta(seconds=1)
    start_local = previous_month_end.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    start_utc, end_utc = start_local.astimezone(UTC), end_local.astimezone(UTC)
    key = f"monthly:{start_local.strftime('%Y-%m')}"
    if get_last_report(key):
        print("Monthly report already sent.")
        return
    send_message(report_text("Monthly", start_utc, end_utc))
    save_report(key)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("task", choices=["scan", "weekly", "monthly", "reports"])
    task = parser.parse_args().task
    if task == "scan":
        run_scan()
    elif task == "weekly":
        run_weekly()
    elif task == "monthly":
        run_monthly()
    elif task == "reports":
        # One low-cost daily Cron Job handles both report schedules.
        local_now = datetime.now(UTC).astimezone(WIB)
        if local_now.weekday() == 6:
            run_weekly()
        if local_now.day == 1:
            run_monthly()
