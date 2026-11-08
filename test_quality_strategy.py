
import pytest
import math

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
# ==========================================
# ADVANCED QUALITY EDITION TESTS
# ==========================================

def make_test_indicators(
    fast,
    slow,
    ema13=101,
    ema21=104,
    ema50=103,
    atr=2,
    adx=25,
):
    return {
        "fast": fast,
        "slow": slow,
        "pullback": [ema13] * len(fast),
        "ema21": [ema21] * len(fast),
        "ema50": [ema50] * len(fast),
        "atr": [atr] * len(fast),
        "adx": [adx] * len(fast),
    }


def test_adx_strong_one_directional_market():
    high = [100.0 + i for i in range(40)]
    low = [98.0 + i for i in range(40)]
    close = [99.0 + i for i in range(40)]

    result = calculate_adx(high, low, close, 14)

    assert result["plus_di"][27] == pytest.approx(50.0)
    assert result["minus_di"][27] == pytest.approx(0.0)
    assert result["dx"][27] == pytest.approx(100.0)
    assert result["adx"][27] == pytest.approx(100.0)


def test_modified_crossover_buy():
    candles = [
    {
        "open": 100,
        "high": 106,
        "low": 99,
        "close": 105,
    },
    {
        "open": 100,
        "high": 106,
        "low": 99,
        "close": 105,
    },
]

    ind = make_test_indicators(
        fast=[100, 103],
        slow=[101, 102],
        ema21=102,
        ema50=101,
        adx=25,
    )

    assert detect_modified_crossover(candles, ind, 1) == "BUY"



def test_modified_crossover_sell():
    candles = [
        {
            "open": 105,
            "high": 106,
            "low": 99,
            "close": 100,
        },
        {
            "open": 105,
            "high": 106,
            "low": 99,
            "close": 100,
        },
    ]

    ind = make_test_indicators(
        fast=[103, 100],
        slow=[102, 101],
        ema21=101,
        ema50=102,
        adx=25,
    )

    assert detect_modified_crossover(candles, ind, 1) == "SELL"


def test_modified_crossover_does_not_require_wick_rejection():
    candles = [
    {
        "open": 100,
        "high": 106,
        "low": 99,
        "close": 105,
    },
    {
        "open": 100,
        "high": 106,
        "low": 99,
        "close": 105,
    },
]

    ind = make_test_indicators(
        fast=[100, 103],
        slow=[101, 102],
        ema21=102,
        ema50=101,
        adx=25,
    )

    confirmation = validate_candle(candles[0])

    assert confirmation["lower_wick"] < confirmation["body"]
    assert detect_modified_crossover(candles, ind, 1) == "BUY"


def test_modified_crossover_rejects_adx_below_20():
    candles = [
    {
        "open": 100,
        "high": 106,
        "low": 99,
        "close": 105,
    },
    {
        "open": 100,
        "high": 106,
        "low": 99,
        "close": 105,
    },
]

    ind = make_test_indicators(
        fast=[100, 103],
        slow=[101, 102],
        ema21=102,
        ema50=101,
        adx=19.99,
    )

    assert detect_modified_crossover(candles, ind, 1) is None


def test_modified_crossover_accepts_adx_exactly_20():
    candles = [
    {
        "open": 100,
        "high": 106,
        "low": 99,
        "close": 105,
    },
    {
        "open": 100,
        "high": 106,
        "low": 99,
        "close": 105,
    },
]

    ind = make_test_indicators(
        fast=[100, 103],
        slow=[101, 102],
        ema21=102,
        ema50=101,
        adx=20.0,
    )

    assert detect_modified_crossover(candles, ind, 1) == "BUY"


def test_pullback_ema13_buy():
    candles = [{
        "open": 102,
        "high": 107,
        "low": 97,
        "close": 106,
    }]

    ind = make_test_indicators(
        fast=[100],
        slow=[101],
        ema13=101,
        ema21=104,
        ema50=103,
        adx=25,
    )

    assert detect_pullback_ema13(candles, ind, 0) == "BUY"


def test_pullback_ema13_sell():
    candles = [{
        "open": 106,
        "high": 111,
        "low": 101,
        "close": 102,
    }]

    ind = make_test_indicators(
        fast=[100],
        slow=[101],
        ema13=107,
        ema21=104,
        ema50=105,
        adx=25,
    )

    assert detect_pullback_ema13(candles, ind, 0) == "SELL"


def test_pullback_rejects_missing_wick_rejection():
    candles = [{
        "open": 102,
        "high": 107,
        "low": 100,
        "close": 106,
    }]

    ind = make_test_indicators(
        fast=[100],
        slow=[101],
        ema13=101,
        ema21=104,
        ema50=103,
        adx=25,
    )

    confirmation = validate_candle(candles[0])

    assert confirmation["lower_wick"] < confirmation["body"]
    assert detect_pullback_ema13(candles, ind, 0) is None


def test_pullback_rejects_adx_below_20():
    candles = [{
        "open": 102,
        "high": 107,
        "low": 97,
        "close": 106,
    }]

    ind = make_test_indicators(
        fast=[100],
        slow=[101],
        ema13=101,
        ema21=104,
        ema50=103,
        adx=19.99,
    )

    assert detect_pullback_ema13(candles, ind, 0) is None


def test_pullback_rejects_wrong_trend():
    candles = [{
        "open": 102,
        "high": 107,
        "low": 97,
        "close": 106,
    }]

    ind = make_test_indicators(
        fast=[100],
        slow=[101],
        ema13=101,
        ema21=103,
        ema50=104,
        adx=25,
    )

    assert detect_pullback_ema13(candles, ind, 0) is None
def test_adx14_against_independent_reference_values():
    high = []
    low = []
    close = []

    for i in range(50):
        c = 2000 + 0.35 * i + 2.2 * math.sin(i * 0.7)
        o = c - 0.4 * math.cos(i * 0.31)

        high.append(max(o, c) + 0.8 + 0.15 * (i % 3))
        low.append(min(o, c) - 0.7 - 0.1 * (i % 4))
        close.append(c)

    result = calculate_adx(high, low, close, 14)

    reference = {
        27: (32.1664832473, 12.5765699904, 43.7831391453, 37.9015865073),
        28: (35.3645655597, 11.4074894559, 51.2209183365, 38.8529673522),
        35: (28.5800435952, 13.8921486466, 34.5823800783, 38.6290018634),
        49: (31.3235497170, 12.9628489601, 41.4590061628, 40.7740750241),
    }

    for index, expected in reference.items():
        actual = (
            result["plus_di"][index],
            result["minus_di"][index],
            result["dx"][index],
            result["adx"][index],
        )

        for actual_value, expected_value in zip(actual, expected):
            assert actual_value == pytest.approx(
                expected_value, abs=1e-8
            )
