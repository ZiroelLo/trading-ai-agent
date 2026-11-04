import os
import requests
from datetime import datetime, timezone, timedelta


def get_closed_candles():
    api_key = os.getenv("TWELVE_DATA_API_KEY")
    if not api_key:
        raise RuntimeError("Environment variable TWELVE_DATA_API_KEY belum diisi.")

    symbol = os.getenv("SYMBOL", "XAU/USD")
    response = requests.get(
        "https://api.twelvedata.com/time_series",
        params={
            "symbol": symbol,
            "interval": "30min",
            "outputsize": 180,
            "timezone": "UTC",
            "apikey": api_key,
        },
        timeout=30,
    )
    response.raise_for_status()
    payload = response.json()
    if "values" not in payload:
        raise RuntimeError(f"Twelve Data tidak mengembalikan candle: {payload}")

    now = datetime.now(timezone.utc)
    candles = []
    for row in reversed(payload["values"]):
        t = datetime.strptime(row["datetime"], "%Y-%m-%d %H:%M:%S").replace(
            tzinfo=timezone.utc
        )
        # Only accept bars whose full 30-minute interval has ended.
        if t + timedelta(minutes=30) > now:
            continue
        candles.append({
            "time": t,
            "open": float(row["open"]),
            "high": float(row["high"]),
            "low": float(row["low"]),
            "close": float(row["close"]),
        })

    if len(candles) < 60:
        raise RuntimeError(
            "Data candle M30 tertutup kurang dari 60. Periksa akses XAU/USD "
            "dan paket API provider."
        )
    return candles
