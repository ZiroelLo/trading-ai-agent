def ema(values, period):
    alpha = 2.0 / (period + 1.0)
    result = [values[0]]
    for value in values[1:]:
        result.append(alpha * value + (1.0 - alpha) * result[-1])
    return result


def rma(values, period):
    """Wilder RMA, corresponding to TradingView ta.atr smoothing."""
    out = [None] * len(values)
    if len(values) < period:
        return out
    out[period - 1] = sum(values[:period]) / period
    for i in range(period, len(values)):
        out[i] = (out[i - 1] * (period - 1) + values[i]) / period
    return out


def calculate_indicators(candles):
    close = [c["close"] for c in candles]
    high = [c["high"] for c in candles]
    low = [c["low"] for c in candles]
    hlc3 = [(high[i] + low[i] + close[i]) / 3 for i in range(len(candles))]

    true_range = [high[0] - low[0]]
    for i in range(1, len(candles)):
        true_range.append(max(
            high[i] - low[i],
            abs(high[i] - close[i - 1]),
            abs(low[i] - close[i - 1])
        ))

    return {
        "fast": ema(hlc3, 1),
        "slow": ema(hlc3, 3),
        "trend": ema(hlc3, 21),
        "pullback": ema(close, 13),
        "atr": rma(true_range, 14),
    }


def detect_signals(candles, ind):
    i = len(candles) - 1
    if i < 25 or ind["atr"][i] is None:
        return []

    price = candles[i]["close"]
    long_trend = price > ind["trend"][i]
    short_trend = price < ind["trend"][i]

    long_cross = (
        ind["fast"][i - 1] <= ind["slow"][i - 1]
        and ind["fast"][i] > ind["slow"][i]
        and long_trend
    )
    short_cross = (
        ind["fast"][i - 1] >= ind["slow"][i - 1]
        and ind["fast"][i] < ind["slow"][i]
        and short_trend
    )

    long_pullback = (
        candles[i]["low"] <= ind["pullback"][i]
        and price > ind["pullback"][i]
        and long_trend
    )
    short_pullback = (
        candles[i]["high"] >= ind["pullback"][i]
        and price < ind["pullback"][i]
        and short_trend
    )

    signals = []
    if long_cross:
        signals.append(("Modified Crossover", "BUY"))
    if short_cross:
        signals.append(("Modified Crossover", "SELL"))
    if long_pullback:
        signals.append(("Pullback EMA13", "BUY"))
    if short_pullback:
        signals.append(("Pullback EMA13", "SELL"))
    return signals
