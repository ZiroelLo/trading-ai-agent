import math
def ema(values, period):
    """EMA seeded with the first available value."""
    if period < 1:
        raise ValueError("EMA period must be >= 1")
    if not values:
        return []

    alpha = 2.0 / (period + 1.0)
    result = [float(values[0])]

    for value in values[1:]:
        result.append(
            alpha * float(value) + (1.0 - alpha) * result[-1]
        )

    return result


def rma(values, period):
    """Wilder's RMA, seeded with the first period SMA."""
    if period < 1:
        raise ValueError("RMA period must be >= 1")

    out = [None] * len(values)

    if len(values) < period:
        return out

    out[period - 1] = sum(values[:period]) / period

    for i in range(period, len(values)):
        out[i] = (
            out[i - 1] * (period - 1) + values[i]
        ) / period

    return out


def calculate_atr(high, low, close, period=14):
    if not (len(high) == len(low) == len(close)):
        raise ValueError("OHLC arrays must have equal lengths")

    if not close:
        return []

    true_range = [high[0] - low[0]]

    for i in range(1, len(close)):
        true_range.append(max(
            high[i] - low[i],
            abs(high[i] - close[i - 1]),
            abs(low[i] - close[i - 1]),
        ))

    return rma(true_range, period)


def calculate_adx(high, low, close, period=14):
    """
    Wilder ADX:
    True Range, +DM, -DM, +DI, -DI, DX, and ADX.
    ADX seed is the SMA of the first `period` valid DX values.
    """
    n = len(close)

    if not (len(high) == len(low) == n):
        raise ValueError("OHLC arrays must have equal lengths")

    if period < 1:
        raise ValueError("ADX period must be >= 1")

    adx = [None] * n
    plus_di = [None] * n
    minus_di = [None] * n
    dx = [None] * n

    if n <= period:
        return {
            "adx": adx,
            "plus_di": plus_di,
            "minus_di": minus_di,
            "dx": dx,
        }

    tr = [0.0] * n
    plus_dm = [0.0] * n
    minus_dm = [0.0] * n

    for i in range(1, n):
        up_move = high[i] - high[i - 1]
        down_move = low[i - 1] - low[i]

        plus_dm[i] = (
            up_move if up_move > down_move and up_move > 0 else 0.0
        )
        minus_dm[i] = (
            down_move if down_move > up_move and down_move > 0 else 0.0
        )

        tr[i] = max(
            high[i] - low[i],
            abs(high[i] - close[i - 1]),
            abs(low[i] - close[i - 1]),
        )

    smoothed_tr = [None] * n
    smoothed_plus = [None] * n
    smoothed_minus = [None] * n

    # First Wilder sums use the first `period` transitions.
    smoothed_tr[period] = sum(tr[1:period + 1])
    smoothed_plus[period] = sum(plus_dm[1:period + 1])
    smoothed_minus[period] = sum(minus_dm[1:period + 1])

    for i in range(period + 1, n):
        smoothed_tr[i] = (
            smoothed_tr[i - 1]
            - smoothed_tr[i - 1] / period
            + tr[i]
        )
        smoothed_plus[i] = (
            smoothed_plus[i - 1]
            - smoothed_plus[i - 1] / period
            + plus_dm[i]
        )
        smoothed_minus[i] = (
            smoothed_minus[i - 1]
            - smoothed_minus[i - 1] / period
            + minus_dm[i]
        )

    for i in range(period, n):
        if smoothed_tr[i] == 0:
            plus_di[i] = 0.0
            minus_di[i] = 0.0
            dx[i] = 0.0
            continue

        plus_di[i] = 100.0 * smoothed_plus[i] / smoothed_tr[i]
        minus_di[i] = 100.0 * smoothed_minus[i] / smoothed_tr[i]

        denominator = plus_di[i] + minus_di[i]

        dx[i] = (
            100.0 * abs(plus_di[i] - minus_di[i]) / denominator
            if denominator > 0 else 0.0
        )

    first_adx_index = period * 2 - 1

    if first_adx_index >= n:
        return {
            "adx": adx,
            "plus_di": plus_di,
            "minus_di": minus_di,
            "dx": dx,
        }

    first_dx_values = dx[period:first_adx_index + 1]

    if len(first_dx_values) != period or any(
        value is None for value in first_dx_values
    ):
        return {
            "adx": adx,
            "plus_di": plus_di,
            "minus_di": minus_di,
            "dx": dx,
        }

    adx[first_adx_index] = sum(first_dx_values) / period

    for i in range(first_adx_index + 1, n):
        adx[i] = (
            adx[i - 1] * (period - 1) + dx[i]
        ) / period

    return {
        "adx": adx,
        "plus_di": plus_di,
        "minus_di": minus_di,
        "dx": dx,
    }


def calculate_quality_indicators(candles):
    if not candles:
        raise ValueError("Candles cannot be empty")

    close = [float(c["close"]) for c in candles]
    high = [float(c["high"]) for c in candles]
    low = [float(c["low"]) for c in candles]

    hlc3 = [
        (high[i] + low[i] + close[i]) / 3.0
        for i in range(len(candles))
    ]

    adx_data = calculate_adx(high, low, close, 14)

    return {
        "fast": ema(hlc3, 1),
        "slow": ema(hlc3, 3),
        "pullback": ema(close, 13),
        "ema21": ema(close, 21),
        "ema50": ema(close, 50),
        "atr": calculate_atr(high, low, close, 14),
        "adx": adx_data["adx"],
        "plus_di": adx_data["plus_di"],
        "minus_di": adx_data["minus_di"],
    }




def validate_candle(candle):
    open_price = float(candle["open"])
    close_price = float(candle["close"])
    high = float(candle["high"])
    low = float(candle["low"])

    invalid_result = {
        "valid": False,
        "body_ratio": 0.0,
        "body": 0.0,
        "lower_wick": 0.0,
        "upper_wick": 0.0,
        "bullish": False,
        "bearish": False,
    }

    prices = (open_price, high, low, close_price)

    # Reject NaN and Infinity
    if not all(math.isfinite(price) for price in prices):
        return invalid_result

    # Validate OHLC consistency
    if high < max(open_price, close_price):
        return invalid_result

    if low > min(open_price, close_price):
        return invalid_result

    candle_range = high - low
    body = abs(close_price - open_price)

    if candle_range <= 0:
        return invalid_result

    return {
        "valid": True,
        "body_ratio": body / candle_range,
        "body": body,
        "lower_wick": min(open_price, close_price) - low,
        "upper_wick": high - max(open_price, close_price),
        "bullish": close_price > open_price,
        "bearish": close_price < open_price,
    }



def detect_modified_crossover(candles, ind, i=None):
    if i is None:
        i = len(candles) - 1

    if i < 1:
        return None

    required = (
        ind["atr"][i],
        ind["adx"][i],
        ind["ema21"][i],
        ind["ema50"][i],
    )

    if any(value is None for value in required):
        return None

    candle = candles[i]
    confirmation = validate_candle(candle)

    if not confirmation["valid"]:
        return None

    if confirmation["body_ratio"] < 0.40:
        return None

    if ind["adx"][i] < 20:
        return None

    fast_previous = ind["fast"][i - 1]
    slow_previous = ind["slow"][i - 1]
    fast_current = ind["fast"][i]
    slow_current = ind["slow"][i]

    close = candle["close"]

    if (
        fast_previous <= slow_previous
        and fast_current > slow_current
        and close > ind["ema21"][i]
        and ind["ema21"][i] > ind["ema50"][i]
        and confirmation["bullish"]
    ):
        return "BUY"

    if (
        fast_previous >= slow_previous
        and fast_current < slow_current
        and close < ind["ema21"][i]
        and ind["ema21"][i] < ind["ema50"][i]
        and confirmation["bearish"]
    ):
        return "SELL"

    return None


def detect_pullback_ema13(candles, ind, i=None):
    if i is None:
        i = len(candles) - 1

    if i < 0:
        return None

    required = (
        ind["atr"][i],
        ind["adx"][i],
        ind["ema21"][i],
        ind["ema50"][i],
        ind["pullback"][i],
    )

    if any(value is None for value in required):
        return None

    candle = candles[i]
    confirmation = validate_candle(candle)

    if not confirmation["valid"]:
        return None

    if confirmation["body_ratio"] < 0.40:
        return None

    if ind["adx"][i] < 20:
        return None

    close = candle["close"]
    ema13 = ind["pullback"][i]
    ema21 = ind["ema21"][i]
    ema50 = ind["ema50"][i]

    if (
        ema21 > ema50
        and close > ema21
        and close > ema50
        and candle["low"] <= ema13
        and close > ema13
        and confirmation["bullish"]
        and confirmation["lower_wick"] >= confirmation["body"]
    ):
        return "BUY"

    if (
        ema21 < ema50
        and close < ema21
        and close < ema50
        and candle["high"] >= ema13
        and close < ema13
        and confirmation["bearish"]
        and confirmation["upper_wick"] >= confirmation["body"]
    ):
        return "SELL"

    return None


def detect_quality_signals(candles, ind, i=None):
    if i is None:
        i = len(candles) - 1

    if i < 0 or i >= len(candles):
        return []

    signals = []

    crossover = detect_modified_crossover(candles, ind, i)
    pullback = detect_pullback_ema13(candles, ind, i)

    if crossover:
        signals.append(("Modified Crossover", crossover))

    if pullback:
        signals.append(("Pullback EMA13", pullback))

    return signals
