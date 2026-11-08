
from datetime import datetime, timedelta, timezone

from chart import make_signal_chart


def test_quality_chart_generates_png():
    candles = []
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)

    for i in range(70):
        price = 2000 + i * 0.5

        candles.append({
            "time": start + timedelta(minutes=30 * i),
            "open": price,
            "high": price + 2,
            "low": price - 1,
            "close": price + 1,
        })

    indicators = {
        "fast": [2000 + i * 0.5 for i in range(70)],
        "slow": [2000 + i * 0.4 for i in range(70)],
        "pullback": [2000 + i * 0.45 for i in range(70)],
        "ema21": [2000 + i * 0.4 for i in range(70)],
        "ema50": [2000 + i * 0.3 for i in range(70)],
        "adx": [25.0] * 70,
        "plus_di": [30.0] * 70,
        "minus_di": [15.0] * 70,
    }

    chart = make_signal_chart(
        candles,
        indicators,
        "Modified Crossover",
        "BUY",
        2035.0,
        2030.0,
        2045.0,
    )

    assert chart.read(8) == b"\x89PNG\r\n\x1a\n"
    assert chart.tell() == 8


def test_quality_chart_rejects_missing_indicators():
    try:
        make_signal_chart(
            [{"time": datetime.now(timezone.utc)}],
            {},
            "Test",
            "BUY",
            2000,
            1990,
            2020,
        )
    except ValueError as error:
        assert "Missing indicators" in str(error)
    else:
        raise AssertionError(
            "Missing indicators should raise ValueError"
        )
