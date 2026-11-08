
import pytest

from quality_strategy import (
    ema,
    rma,
    calculate_atr,
    calculate_adx,
    calculate_quality_indicators,
    validate_candle,
    detect_modified_crossover,
    detect_pullback_ema13,
    detect_quality_signals,
)


def test_ema_period_one_equals_input():
    values = [10, 12, 15, 14]
    assert ema(values, 1) == values


def test_ema_empty_input():
    assert ema([], 3) == []


def test_rma_seed_and_smoothing():
    result = rma([1, 2, 3, 4], 3)
    assert result[:2] == [None, None]
    assert result[2] == pytest.approx(2.0)
    assert result[3] == pytest.approx(8 / 3)


def test_atr_constant_range():
    high = [11.0] * 20
    low = [9.0] * 20
    close = [10.0] * 20

    result = calculate_atr(high, low, close, 14)

    assert result[13] == pytest.approx(2.0)


def test_adx_constant_market_is_zero():
    high = [10.0] * 40
    low = [10.0] * 40
    close = [10.0] * 40

    result = calculate_adx(high, low, close, 14)

    assert result["adx"][27] == pytest.approx(0.0)


def test_adx_first_valid_index():
    high = [float(100 + i) for i in range(40)]
    low = [float(98 + i) for i in range(40)]
    close = [float(99 + i) for i in range(40)]

    result = calculate_adx(high, low, close, 14)

    assert all(v is None for v in result["adx"][:27])
    assert result["adx"][27] is not None


def test_candle_body_ratio_39_percent():
    candle = {
        "open": 100,
        "high": 110,
        "low": 100,
        "close": 103.9,
    }

    result = validate_candle(candle)

    assert result["valid"]
    assert result["body_ratio"] == pytest.approx(0.39)
    assert result["body_ratio"] < 0.40


def test_candle_body_ratio_40_percent():
    candle = {
        "open": 100,
        "high": 110,
        "low": 100,
        "close": 104,
    }

    result = validate_candle(candle)

    assert result["body_ratio"] == pytest.approx(0.40)


def test_zero_range_candle_invalid():
    candle = {
        "open": 100,
        "high": 100,
        "low": 100,
        "close": 100,
    }

    assert validate_candle(candle)["valid"] is False


def test_bullish_candle_detection():
    candle = {
        "open": 100,
        "high": 110,
        "low": 95,
        "close": 108,
    }

    result = validate_candle(candle)

    assert result["bullish"] is True
    assert result["bearish"] is False


def test_bearish_candle_detection():
    candle = {
        "open": 108,
        "high": 110,
        "low": 95,
        "close": 100,
    }

    result = validate_candle(candle)

    assert result["bearish"] is True
    assert result["bullish"] is False


def test_pullback_wick_rejection_measurement():
    candle = {
        "open": 105,
        "high": 106,
        "low": 99,
        "close": 104,
    }

    result = validate_candle(candle)

    assert result["body"] == pytest.approx(1)
    assert result["lower_wick"] == pytest.approx(5)


def test_quality_indicators_keys():
    candles = []

    for i in range(100):
        price = 2000 + i * 0.5
        candles.append({
            "open": price - 0.2,
            "high": price + 1,
            "low": price - 1,
            "close": price,
        })

    result = calculate_quality_indicators(candles)

    expected = {
        "fast", "slow", "pullback",
        "ema21", "ema50", "atr",
        "adx", "plus_di", "minus_di",
    }

    assert set(result.keys()) == expected
    assert len(result["ema50"]) == 100
    assert result["adx"][27] is not None


def test_modified_crossover_rejects_missing_adx():
    candles = [{
        "open": 100,
        "high": 105,
        "low": 99,
        "close": 104,
    }]

    indicators = {
        "fast": [101],
        "slow": [100],
        "ema21": [99],
        "ema50": [98],
        "atr": [1],
        "adx": [None],
    }

    assert detect_modified_crossover(candles, indicators, 0) is None


def test_pullback_rejects_missing_adx():
    candles = [{
        "open": 100,
        "high": 105,
        "low": 99,
        "close": 104,
    }]

    indicators = {
        "pullback": [101],
        "ema21": [99],
        "ema50": [98],
        "atr": [1],
        "adx": [None],
    }

    assert detect_pullback_ema13(candles, indicators, 0) is None


def test_detect_quality_signals_invalid_index():
    assert detect_quality_signals([], {}, 0) == []
