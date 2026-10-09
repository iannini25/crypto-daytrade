"""Coarse long-only pattern labels on closed candles.

These are desk heuristics for the dry-run scanner, not a signal service.
A label is context for a person. The scanner never turns one into an order.

Detection uses the structure bars only. The final bar is the confirmation
close, so a breakout can actually clear resistance (resistance is the max
high of the bars before it, not of the signal bar itself).
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from desk.bybit import Candle

MIN_HEIGHT = Decimal("0.01")

# Catalog from docs/playbook-padroes-v1.md. Active names may become a paper
# long. Exit-only names never open a short and never open a new long.
# Out-of-v1 names are a log, not an entry. Reversals are active only on 1h
# 1h or daily. A 15m bar only confirms the close; it does not draw the pattern.
ACTIVE_LONG = frozenset(
    {
        "ascending_triangle",
        "rectangle",
        "falling_wedge",
        "bull_flag",
        "inverse_head_and_shoulders",
        "double_bottom",
    }
)
REVERSAL_LONG = frozenset({"inverse_head_and_shoulders", "double_bottom"})
OUT_OF_V1 = frozenset({"cup", "symmetric_triangle", "pennant_up", "rounded_bottom"})
EXIT_ONLY = frozenset(
    {
        "descending_triangle",
        "rising_wedge",
        "bear_flag",
        "pennant_down",
        "head_and_shoulders",
        "double_top",
        "rounded_top",
    }
)


def pattern_role(name: str | None) -> str:
    """`active`, `exit_only`, `out`, or `unknown`."""
    if name in EXIT_ONLY:
        return "exit_only"
    if name in OUT_OF_V1:
        return "out"
    if name in ACTIVE_LONG:
        return "active"
    return "unknown"


def long_entry_allowed(name: str | None, timeframe: str) -> bool:
    """True when this name may open a paper long drawn on that timeframe.

    Every active pattern is drawn on 1h or daily. The 15m close only confirms
    the entry. Exit-only and out-of-v1 names never open a long.
    """
    if name not in ACTIVE_LONG:
        return False
    return timeframe in {"1h", "D"}


@dataclass(frozen=True)
class PatternMatch:
    name: str
    support: Decimal
    resistance: Decimal
    target: Decimal
    height_pct: Decimal
    confirmed: bool

    @property
    def height_ok(self) -> bool:
        return self.height_pct >= MIN_HEIGHT


def _box(resistance: Decimal, support: Decimal) -> tuple[Decimal, Decimal]:
    height = resistance - support
    height_pct = height / support if support > 0 else Decimal("0")
    target = resistance + height
    return target, height_pct


def swing_indexes(values: list[Decimal], kind: str) -> list[tuple[int, Decimal]]:
    points: list[tuple[int, Decimal]] = []
    for index in range(1, len(values) - 1):
        left, mid, right = values[index - 1], values[index], values[index + 1]
        if kind == "high" and mid > left and mid > right:
            points.append((index, mid))
        elif kind == "low" and mid < left and mid < right:
            points.append((index, mid))
    return points


def daily_hh_hl(candles: list[Candle]) -> bool:
    """True when the last two swing highs and swing lows are both ascending."""
    if len(candles) < 7:
        return False
    highs = swing_indexes([candle.high for candle in candles], "high")
    lows = swing_indexes([candle.low for candle in candles], "low")
    if len(highs) < 2 or len(lows) < 2:
        return False
    higher_high = highs[-1][1] > highs[-2][1]
    higher_low = lows[-1][1] > lows[-2][1]
    return higher_high and higher_low


def _match(
    name: str,
    support: Decimal,
    resistance: Decimal,
    *,
    target: Decimal | None = None,
    height_pct: Decimal | None = None,
) -> PatternMatch | None:
    if support <= 0 or resistance <= support:
        return None
    box_target, box_height = _box(resistance, support)
    return PatternMatch(
        name=name,
        support=support,
        resistance=resistance,
        target=box_target if target is None else target,
        height_pct=box_height if height_pct is None else height_pct,
        confirmed=False,
    )


def match_inverse_head_and_shoulders(structure: list[Candle]) -> PatternMatch | None:
    if len(structure) < 15:
        return None
    lows = swing_indexes([candle.low for candle in structure], "low")
    if len(lows) < 3:
        return None
    (i1, left), (i2, head), (i3, right) = lows[-3:]
    if i2 - i1 < 2 or i3 - i2 < 2:
        return None
    if head >= left or head >= right:
        return None
    if head > min(left, right) * Decimal("0.997"):
        return None
    if abs(left - right) / min(left, right) > Decimal("0.006"):
        return None
    span = structure[i1 : i3 + 1]
    neck = max(candle.high for candle in span)
    if neck <= max(left, head, right):
        return None
    height = neck - head
    return _match(
        "inverse_head_and_shoulders",
        support=right,
        resistance=neck,
        target=neck + height,
        height_pct=height / head,
    )


def match_double_bottom(structure: list[Candle]) -> PatternMatch | None:
    if len(structure) < 15:
        return None
    lows = swing_indexes([candle.low for candle in structure], "low")
    if len(lows) < 2:
        return None
    i1, first = lows[-2]
    i2, second = lows[-1]
    if i2 - i1 < 3:
        return None
    base = min(first, second)
    if abs(first - second) / base > Decimal("0.004"):
        return None
    neck = max(candle.high for candle in structure[i1 : i2 + 1])
    if neck < base * Decimal("1.01"):
        return None
    height = neck - base
    return _match(
        "double_bottom",
        support=second,
        resistance=neck,
        target=neck + height,
        height_pct=height / base,
    )


def match_cup(structure: list[Candle]) -> PatternMatch | None:
    if len(structure) < 30:
        return None
    window = structure[-30:]
    left = sum((candle.close for candle in window[:3]), Decimal("0")) / 3
    right = sum((candle.close for candle in window[-3:]), Decimal("0")) / 3
    if left <= 0 or abs(right - left) / left > Decimal("0.01"):
        return None
    trough_i = min(range(len(window)), key=lambda index: window[index].low)
    lower = len(window) * 3 // 10
    upper = len(window) * 7 // 10
    if not lower <= trough_i <= upper:
        return None
    trough = window[trough_i].low
    rim_high = max(candle.high for candle in window[:3] + window[-3:])
    if trough > rim_high * Decimal("0.99"):
        return None
    return _match("cup", support=trough, resistance=rim_high)


def match_ascending_triangle(structure: list[Candle]) -> PatternMatch | None:
    if len(structure) < 20:
        return None
    window = structure[-24:]
    highs = [candle.high for candle in window]
    lows = [candle.low for candle in window]
    resistance = max(highs)
    if resistance <= 0:
        return None
    touches = sum(1 for high in highs if (resistance - high) / resistance <= Decimal("0.0015"))
    if touches < 2:
        return None
    mid = len(window) // 2
    left_floor = min(lows[:mid])
    right_floor = min(lows[mid:])
    if right_floor <= left_floor * Decimal("1.002"):
        return None
    left_high = max(highs[:mid])
    right_high = max(highs[mid:])
    if abs(left_high - right_high) / resistance > Decimal("0.002"):
        return None
    return _match("ascending_triangle", support=right_floor, resistance=resistance)


def match_bull_flag(structure: list[Candle]) -> PatternMatch | None:
    if len(structure) < 30:
        return None
    pole = structure[-30:-10]
    flag = structure[-10:]
    pole_low = min(candle.low for candle in pole)
    pole_high = max(candle.high for candle in pole)
    if pole[-1].close < pole[0].close * Decimal("1.01"):
        return None
    if pole_high <= pole_low:
        return None
    half = pole_high - (pole_high - pole_low) * Decimal("0.5")
    flag_low = min(candle.low for candle in flag)
    flag_high = max(candle.high for candle in flag)
    if flag_low < half or flag_high > pole_high:
        return None
    if (flag_high - flag_low) > (pole_high - pole_low) * Decimal("0.6"):
        return None
    if flag[-1].close > flag[0].close * Decimal("1.001"):
        return None
    pole_height = pole[-1].close - pole[0].close
    box_target, height_pct = _box(flag_high, flag_low)
    # Measured move uses the pole. Height for the 1% rule is the flag box,
    # because that is the distance from entry to the stop.
    return _match(
        "bull_flag",
        support=flag_low,
        resistance=flag_high,
        target=flag_high + pole_height,
        height_pct=height_pct if height_pct > 0 else (box_target - flag_high) / flag_low,
    )


def match_falling_wedge(structure: list[Candle]) -> PatternMatch | None:
    if len(structure) < 20:
        return None
    window = structure[-24:]
    mid = len(window) // 2
    left, right = window[:mid], window[mid:]
    left_high = max(candle.high for candle in left)
    right_high = max(candle.high for candle in right)
    left_low = min(candle.low for candle in left)
    right_low = min(candle.low for candle in right)
    if not (right_high < left_high and right_low < left_low):
        return None
    left_range = left_high - left_low
    right_range = right_high - right_low
    if left_range <= 0 or right_range >= left_range * Decimal("0.85"):
        return None
    resistance = max(candle.high for candle in window[-6:])
    return _match("falling_wedge", support=right_low, resistance=resistance)


def match_rectangle(structure: list[Candle]) -> PatternMatch | None:
    if len(structure) < 20:
        return None
    window = structure[-20:]
    resistance = max(candle.high for candle in window)
    support = min(candle.low for candle in window)
    if support <= 0 or resistance <= support:
        return None
    high_touches = sum(
        1 for candle in window if (resistance - candle.high) / resistance <= Decimal("0.0015")
    )
    low_touches = sum(1 for candle in window if (candle.low - support) / support <= Decimal("0.0015"))
    if high_touches < 2 or low_touches < 2:
        return None
    mid = len(window) // 2
    left_mean = sum((candle.close for candle in window[:mid]), Decimal("0")) / mid
    right_count = len(window) - mid
    right_mean = sum((candle.close for candle in window[mid:]), Decimal("0")) / right_count
    if abs(right_mean - left_mean) > (resistance - support) * Decimal("0.35"):
        return None
    return _match("rectangle", support=support, resistance=resistance)


# Specific shapes first so a coil is not labelled a plain box.
_DETECTORS = (
    match_inverse_head_and_shoulders,
    match_double_bottom,
    match_cup,
    match_ascending_triangle,
    match_bull_flag,
    match_falling_wedge,
    match_rectangle,
)


def detect(candles: list[Candle]) -> PatternMatch | None:
    """Pattern drawn on these bars. This does not treat the last bar as a breakout."""
    if len(candles) < 15:
        return None
    for detector in _DETECTORS:
        found = detector(candles)
        if found is not None:
            return found
    return None


def classify(candles: list[Candle]) -> PatternMatch | None:
    """Label the last closed bar as a breakout only when its close clears resistance."""
    if len(candles) < 15:
        return None
    structure = candles[:-1]
    signal = candles[-1]
    found: PatternMatch | None = None
    for detector in _DETECTORS:
        found = detector(structure)
        if found is not None:
            break
    if found is None:
        return None
    confirmed = signal.close > found.resistance
    return PatternMatch(
        name=found.name,
        support=found.support,
        resistance=found.resistance,
        target=found.target,
        height_pct=found.height_pct,
        confirmed=confirmed,
    )
