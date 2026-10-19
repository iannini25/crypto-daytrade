"""Where a long is allowed to hide its stop.

The 15m candle only times the entry. The stop is the latest 1h or daily
swing low under that entry. 3x daily ATR is a ceiling on that distance,
not a stop of its own. Daily longs also need the close above the 100-day average.
"""

from __future__ import annotations

from decimal import Decimal

from desk.bybit import Candle
from desk.patterns import swing_indexes

ATR_PERIOD = 14
SMA_PERIOD = 100
ATR_CEILING_MULTIPLE = Decimal("3")


def sma(candles: list[Candle], period: int = SMA_PERIOD) -> Decimal | None:
    if len(candles) < period:
        return None
    window = candles[-period:]
    return sum((candle.close for candle in window), Decimal("0")) / Decimal(period)


def above_sma100(candles: list[Candle]) -> bool:
    average = sma(candles, SMA_PERIOD)
    if average is None or not candles:
        return False
    return candles[-1].close > average


def atr(candles: list[Candle], period: int = ATR_PERIOD) -> Decimal | None:
    """Simple average of true range. Needs `period` completed steps."""
    if len(candles) < period + 1:
        return None
    window = candles[-(period + 1) :]
    total = Decimal("0")
    for previous, current in zip(window, window[1:]):
        true_range = max(
            current.high - current.low,
            abs(current.high - previous.close),
            abs(current.low - previous.close),
        )
        total += true_range
    return total / Decimal(period)


def atr_ceiling(candles: list[Candle]) -> Decimal | None:
    """Price distance. The stop may not sit farther than this from entry."""
    value = atr(candles, ATR_PERIOD)
    if value is None:
        return None
    return value * ATR_CEILING_MULTIPLE


def structure_stop(
    hourly: list[Candle],
    daily: list[Candle],
    entry: Decimal,
) -> tuple[Decimal, str] | None:
    """Latest swing low strictly below `entry` on the 1h or the daily chart.

    Returns (price, "1h" or "D"). A 15m swing is never considered.
    """
    candidates: list[tuple[int, Decimal, str]] = []
    for name, series in (("1h", hourly), ("D", daily)):
        if len(series) < 3:
            continue
        lows = swing_indexes([candle.low for candle in series], "low")
        if not lows:
            continue
        index, price = lows[-1]
        if price < entry:
            candidates.append((series[index].start_ms, price, name))
    if not candidates:
        return None
    candidates.sort()
    _start, price, name = candidates[-1]
    return price, name
