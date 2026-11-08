
import pytest
from datetime import datetime, timezone

import main


@pytest.fixture
def fake_market(monkeypatch):
    """Isolate scanner from database, API, and Telegram."""

    candle_time = datetime(
        2026, 11, 8, 10, 0,
        tzinfo=timezone.utc
    )

    candles = [{
        "time": candle_time,
        "open": 2650.0,
        "high": 2660.0,
        "low": 2640.0,
        "close": 2655.0,
    }]

    indicators = {
        "atr": [10.0],
    }

    calls = {
        "insert": [],
        "chart": [],
        "photo": [],
        "track": [],
    }

    monkeypatch.setattr(
        main, "is_forex_market_open", lambda: True
    )
    monkeypatch.setattr(
        main, "init_db", lambda: None
    )
    monkeypatch.setattr(
        main, "get_closed_candles", lambda: candles
    )
    monkeypatch.setattr(
        main, "calculate_quality_indicators",
        lambda c: indicators
    )
    monkeypatch.setattr(
        main, "track_open_positions",
        lambda c: calls["track"].append(c)
    )

    monkeypatch.setattr(
        main, "insert_signal",
        lambda *args: (
            calls["insert"].append(args) or 123
        )
    )

    monkeypatch.setattr(
        main, "make_signal_chart",
        lambda *args: (
            calls["chart"].append(args) or "FAKE_CHART"
        )
    )

    monkeypatch.setattr(
        main, "send_photo",
        lambda *args: calls["photo"].append(args)
    )

    return candles, indicators, calls


def test_scan_market_closed(monkeypatch):
    monkeypatch.setattr(
        main, "is_forex_market_open", lambda: False
    )

    monkeypatch.setattr(
        main, "init_db",
        lambda: pytest.fail("Database should not initialize")
    )

    main.run_scan()


def test_scan_no_signal(fake_market, monkeypatch):
    candles, indicators, calls = fake_market

    monkeypatch.setattr(
        main, "detect_quality_signals",
        lambda c, i: []
    )

    main.run_scan()

    assert calls["track"]
    assert calls["insert"] == []
    assert calls["chart"] == []
    assert calls["photo"] == []


@pytest.mark.parametrize(
    "side, expected_sl, expected_tp",
    [
        ("BUY", 2635.0, 2685.0),
        ("SELL", 2670.0, 2625.0),
    ],
)
def test_scan_signal_risk_calculation(
    fake_market,
    monkeypatch,
    side,
    expected_sl,
    expected_tp,
):
    candles, indicators, calls = fake_market

    monkeypatch.setattr(
        main, "detect_quality_signals",
        lambda c, i: [("Test Strategy", side)]
    )

    main.run_scan()

    assert len(calls["insert"]) == 1
    assert len(calls["chart"]) == 1
    assert len(calls["photo"]) == 1

    saved = calls["insert"][0]

    assert saved[0] == "Test Strategy"
    assert saved[1] == side
    assert saved[3] == pytest.approx(2655.0)
    assert saved[4] == pytest.approx(expected_sl)
    assert saved[5] == pytest.approx(expected_tp)
    assert saved[6] == pytest.approx(10.0)
    assert saved[7] == pytest.approx(2.0)


def test_scan_duplicate_signal(
    fake_market,
    monkeypatch,
):
    candles, indicators, calls = fake_market

    monkeypatch.setattr(
        main, "detect_quality_signals",
        lambda c, i: [("Test Strategy", "BUY")]
    )

    monkeypatch.setattr(
        main, "insert_signal",
        lambda *args: None
    )

    main.run_scan()

    assert len(calls["insert"]) == 0
    assert calls["chart"] == []
    assert calls["photo"] == []
