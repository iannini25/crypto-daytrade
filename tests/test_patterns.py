"""Daily filter, playbook labels, and the dry-run scanner."""

from datetime import datetime, timezone
from decimal import Decimal

from desk.bybit import Candle
from desk.patterns import (
    classify,
    daily_hh_hl,
    long_entry_allowed,
    match_ascending_triangle,
    match_bull_flag,
    match_cup,
    match_double_bottom,
    match_falling_wedge,
    match_inverse_head_and_shoulders,
    match_rectangle,
    pattern_role,
)
from desk.risk import AccountSnapshot
from desk.scanner import analyze
from desk.session import in_liquidity_window


def candle(index: int, high, low, close, open_=None, step_ms: int = 900_000) -> Candle:
    high_d = Decimal(str(high))
    low_d = Decimal(str(low))
    close_d = Decimal(str(close))
    open_d = close_d if open_ is None else Decimal(str(open_))
    return Candle(
        start_ms=1_700_000_000_000 + index * step_ms,
        open=open_d,
        high=high_d,
        low=low_d,
        close=close_d,
        volume=Decimal("1"),
        turnover=Decimal("1"),
    )


def test_liquidity_window_bounds():
    assert in_liquidity_window(datetime(2026, 10, 6, 13, 0, tzinfo=timezone.utc))
    assert in_liquidity_window(datetime(2026, 10, 6, 15, 30, tzinfo=timezone.utc))
    assert not in_liquidity_window(datetime(2026, 10, 6, 12, 59, tzinfo=timezone.utc))
    assert not in_liquidity_window(datetime(2026, 10, 6, 15, 31, tzinfo=timezone.utc))


def test_daily_hh_hl():
    highs = [10, 12, 11, 14, 12, 15, 13]
    lows = [8, 9, "8.2", 10, "9.2", 11, 10]
    candles = [candle(i, highs[i], lows[i], (Decimal(str(highs[i])) + Decimal(str(lows[i]))) / 2, step_ms=86_400_000) for i in range(7)]
    assert daily_hh_hl(candles)
    # Replace the 15 high with 13 so the last swing high is under the prior one (16 is not in this series;
    # highs become 10, 12, 11, 14, 12, 13, 13 — wait, 13 is not a swing). Build an explicit lower high.
    lower_high = [
        candle(i, high, low, (Decimal(str(high)) + Decimal(str(low))) / 2, step_ms=86_400_000)
        for i, (high, low) in enumerate(
            [(10, 8), (12, 9), (11, "8.2"), (16, 10), (12, "9.2"), (14, 11), (13, 10)]
        )
    ]
    assert daily_hh_hl(lower_high) is False


def test_ascending_triangle_confirms_on_close_but_is_not_two_r():
    structure = []
    for index in range(24):
        low = 97 + index * Decimal("0.05")
        structure.append(candle(index, 100, low, (low + 100) / 2))
    signal = candle(24, "100.3", "99.5", "100.1")
    found = match_ascending_triangle(structure)
    assert found is not None
    assert found.name == "ascending_triangle"
    assert found.height_pct >= Decimal("0.01")
    labelled = classify(structure + [signal])
    assert labelled is not None
    assert labelled.name == "ascending_triangle"
    assert labelled.confirmed

    account = AccountSnapshot(equity=Decimal("20"), starting_equity=Decimal("20"))
    daily = _uptrend_daily()
    row = analyze(
        "BTCUSDT",
        daily,
        [],
        structure + [signal],
        account,
        datetime(2026, 10, 6, 14, 0, tzinfo=timezone.utc),
    )
    assert row.daily_hh_hl
    assert row.close_confirmed is False
    assert row.in_window
    assert row.disposition == "watch"
    assert row.pattern is None
    assert any("1h or daily" in note for note in row.notes)


def test_bull_flag_can_be_a_paper_candidate_inside_the_window():
    structure = []
    for index in range(20):
        close = Decimal("100") + Decimal(index) * Decimal("0.5")
        structure.append(candle(index, close + Decimal("0.2"), close - Decimal("0.3"), close))
    for index in range(20, 30):
        close = Decimal("108.8") - Decimal(index - 20) * Decimal("0.06")
        structure.append(candle(index, Decimal("109"), Decimal("107"), close))
    signal = candle(30, "109.2", "108.5", "109.1")
    found = match_bull_flag(structure)
    assert found is not None
    assert found.height_pct >= Decimal("0.01")
    labelled = classify(structure + [signal])
    assert labelled is not None and labelled.name == "bull_flag" and labelled.confirmed

    account = AccountSnapshot(equity=Decimal("19.9"), starting_equity=Decimal("19.9"))
    when = datetime(2026, 10, 6, 14, 0, tzinfo=timezone.utc)
    fifteen_only = analyze(
        "BTCUSDT",
        _uptrend_daily(),
        [],
        structure + [signal],
        account,
        when,
    )
    assert fifteen_only.disposition != "paper_candidate"
    assert fifteen_only.pattern is None
    assert any("1h or daily" in note for note in fifteen_only.notes)

    daily, _unused = _daily_and_hourly_for(Decimal("110"))
    hourly = _hourly_bull_flag(daily[-1].start_ms)
    m15 = [candle(0, "110.2", "109.6", "110")]
    inside = analyze("BTCUSDT", daily, hourly, m15, account, when)
    assert inside.pattern == "bull_flag"
    assert inside.disposition == "paper_candidate"
    assert inside.above_sma100
    assert inside.close_confirmed
    assert inside.stop_anchor == "1h"
    assert inside.rr_after_fees is not None and inside.rr_after_fees >= Decimal("2")
    assert any("no order sent" in note for note in inside.notes)

    outside = analyze(
        "BTCUSDT",
        daily,
        hourly,
        m15,
        account,
        datetime(2026, 10, 6, 2, 0, tzinfo=timezone.utc),
    )
    assert outside.disposition == "watch"
    assert outside.in_window is False

    no_trend = analyze(
        "BTCUSDT",
        [candle(i, 10, 9, Decimal("9.5"), step_ms=86_400_000) for i in range(12)],
        hourly,
        m15,
        account,
        when,
    )
    assert no_trend.disposition == "ignore"
    assert no_trend.daily_hh_hl is False


def test_15m_reversal_and_cup_are_not_paper_candidates():
    assert pattern_role("bull_flag") == "active"
    assert pattern_role("double_top") == "exit_only"
    assert pattern_role("cup") == "out"
    assert long_entry_allowed("bull_flag", "15m") is False
    assert long_entry_allowed("bull_flag", "1h")
    assert long_entry_allowed("double_bottom", "15m") is False
    assert long_entry_allowed("double_bottom", "D")
    assert long_entry_allowed("bear_flag", "1h") is False

    bars = []
    for index in range(16):
        low = Decimal("100")
        high = Decimal("101")
        close = Decimal("100.5")
        if index == 3:
            low, high, close = Decimal("98"), Decimal("99"), Decimal("98.4")
        elif index == 6:
            low, high, close = Decimal("100"), Decimal("100.5"), Decimal("100.2")
        elif index == 9:
            low, high, close = Decimal("98.05"), Decimal("99"), Decimal("98.5")
        elif index in (4, 5, 7, 8):
            low, high, close = Decimal("99"), Decimal("101.2"), Decimal("100")
        bars.append(candle(index, high, low, close))
    signal = candle(16, "102", "101", "101.5")
    account = AccountSnapshot(equity=Decimal("19.9"), starting_equity=Decimal("19.9"))
    row = analyze(
        "BTCUSDT",
        _uptrend_daily(),
        [],
        bars + [signal],
        account,
        datetime(2026, 10, 6, 14, 0, tzinfo=timezone.utc),
    )
    assert row.pattern != "double_bottom"
    assert row.disposition == "watch"
    assert any("1h or daily" in note for note in row.notes)

    cup = []
    for index in range(30):
        x = (Decimal(index) - Decimal("14.5")) / Decimal("14.5")
        low = Decimal("95") + (x * x) * Decimal("5")
        cup.append(candle(index, low + Decimal("0.4"), low, low + Decimal("0.2")))
    cup_row = analyze(
        "ETHUSDT",
        _uptrend_daily(),
        [],
        cup + [candle(30, "101", "100", "100.6")],
        account,
        datetime(2026, 10, 6, 14, 0, tzinfo=timezone.utc),
    )
    assert cup_row.pattern is None
    assert cup_row.disposition != "paper_candidate"
    assert any("1h or daily" in note for note in cup_row.notes)


def test_double_bottom_neckline():
    bars = []
    # Swing lows at indexes 3 and 9, neckline high between them.
    for index in range(16):
        low = Decimal("100")
        high = Decimal("101")
        close = Decimal("100.5")
        if index == 3:
            low, high, close = Decimal("98"), Decimal("99"), Decimal("98.4")
        elif index == 6:
            low, high, close = Decimal("100"), Decimal("100.5"), Decimal("100.2")
        elif index == 9:
            low, high, close = Decimal("98.05"), Decimal("99"), Decimal("98.5")
        elif index in (4, 5, 7, 8):
            low, high, close = Decimal("99"), Decimal("101.2"), Decimal("100")
        bars.append(candle(index, high, low, close))
    found = match_double_bottom(bars)
    assert found is not None
    assert found.name == "double_bottom"
    assert found.resistance >= Decimal("101")
    assert found.height_pct >= Decimal("0.01")


def test_wedge_cup_inverse_head_and_shoulders_and_rectangle():
    wedge = []
    for index in range(12):
        high = Decimal("112") - Decimal(index) * Decimal("0.5")
        low = Decimal("100") - Decimal(index) * Decimal("0.3")
        wedge.append(candle(index, high, low, (high + low) / 2))
    for index in range(12, 24):
        step = index - 12
        high = Decimal("105") - Decimal(step) * Decimal("0.25")
        low = Decimal("95.5") - Decimal(step) * Decimal("0.08")
        wedge.append(candle(index, high, low, (high + low) / 2))
    assert match_falling_wedge(wedge).name == "falling_wedge"

    cup = []
    for index in range(30):
        x = (Decimal(index) - Decimal("14.5")) / Decimal("14.5")
        low = Decimal("95") + (x * x) * Decimal("5")
        cup.append(candle(index, low + Decimal("0.4"), low, low + Decimal("0.2")))
    assert match_cup(cup).height_pct >= Decimal("0.01")

    inverse = []
    for index in range(21):
        high, low, close = Decimal("102"), Decimal("100"), Decimal("101")
        if index == 4:
            high, low, close = Decimal("99"), Decimal("98"), Decimal("98.5")
        elif index == 10:
            high, low, close = Decimal("97"), Decimal("96"), Decimal("96.4")
        elif index == 16:
            high, low, close = Decimal("99"), Decimal("98.1"), Decimal("98.4")
        elif index in (7, 13):
            high, low, close = Decimal("104"), Decimal("100"), Decimal("103")
        inverse.append(candle(index, high, low, close))
    found = match_inverse_head_and_shoulders(inverse)
    assert found is not None
    assert found.name == "inverse_head_and_shoulders"
    assert found.support == Decimal("98.1")

    rectangle = []
    for index in range(20):
        if index % 5 == 0:
            high, low, close = Decimal("100"), Decimal("97"), Decimal("98.5")
        elif index % 5 == 2:
            high, low, close = Decimal("99.9"), Decimal("97.05"), Decimal("98")
        else:
            high, low, close = Decimal("99.5"), Decimal("97.4"), Decimal("98.4")
        rectangle.append(candle(index, high, low, close))
    assert match_rectangle(rectangle).name == "rectangle"


def _hourly_bull_flag(after_ms: int) -> list[Candle]:
    """1h bull flag whose base is 3.5% under a 110 breakout. Not a 15m drawing."""
    bars: list[Candle] = []
    for index in range(20):
        close = Decimal("100") + Decimal(index) * Decimal("9.2") / Decimal("19")
        high = close + Decimal("0.6")
        bars.append(candle(index, high, close - Decimal("0.4"), close, step_ms=3_600_000))
    flag_closes = [
        Decimal("109"),
        Decimal("108.8"),
        Decimal("108.7"),
        Decimal("108.6"),
        Decimal("108.5"),
        Decimal("108.4"),
        Decimal("108.3"),
        Decimal("108.2"),
        Decimal("107.4"),
        Decimal("108.8"),
    ]
    for offset, close in enumerate(flag_closes):
        low = Decimal("106.15") if offset == 8 else close - Decimal("0.3")
        bars.append(candle(20 + offset, Decimal("109.5"), low, close, step_ms=3_600_000))
    origin = bars[0].start_ms
    shifted: list[Candle] = []
    for bar in bars:
        shifted.append(
            Candle(
                start_ms=after_ms + (bar.start_ms - origin) + 3_600_000,
                open=bar.open,
                high=bar.high,
                low=bar.low,
                close=bar.close,
                volume=bar.volume,
                turnover=bar.turnover,
            )
        )
    return shifted


def _daily_and_hourly_for(entry: Decimal) -> tuple[list[Candle], list[Candle]]:
    """Rising daily book above SMA100, plus a later 1h swing about 3.5% under entry."""
    daily: list[Candle] = []
    for index in range(103):
        close = Decimal("70") + Decimal(index) * Decimal("0.3")
        daily.append(
            candle(index, close + Decimal("2"), close - Decimal("2"), close, step_ms=86_400_000)
        )
    tail = [
        (Decimal("108"), Decimal("104"), Decimal("106")),
        (Decimal("112"), Decimal("107"), Decimal("110")),
        (Decimal("109"), Decimal("105"), Decimal("107")),
        (Decimal("115"), Decimal("108"), Decimal("112")),
        (Decimal("111"), Decimal("106"), Decimal("109")),
        (Decimal("118"), Decimal("110"), Decimal("114")),
        (Decimal("113"), Decimal("108"), Decimal("111")),
    ]
    for offset, (high, low, close) in enumerate(tail):
        daily.append(candle(103 + offset, high, low, close, step_ms=86_400_000))
    stop = entry * Decimal("0.965")
    hourly = []
    base = daily[-1].start_ms
    for index in range(30):
        low = entry - Decimal("1")
        high = entry
        close = entry - Decimal("0.4")
        if index == 20:
            low = stop
            high = stop + Decimal("0.4")
            close = stop + Decimal("0.2")
        bar = candle(index, high, low, close, step_ms=3_600_000)
        hourly.append(
            Candle(
                start_ms=base + (index + 1) * 3_600_000,
                open=bar.open,
                high=bar.high,
                low=bar.low,
                close=bar.close,
                volume=bar.volume,
                turnover=bar.turnover,
            )
        )
    return daily, hourly


def _uptrend_daily() -> list[Candle]:
    highs = [10, 12, 11, 14, 12, 15, 13]
    lows = [8, 9, "8.2", 10, "9.2", 11, 10]
    return [
        candle(
            i,
            highs[i],
            lows[i],
            (Decimal(str(highs[i])) + Decimal(str(lows[i]))) / 2,
            step_ms=86_400_000,
        )
        for i in range(7)
    ]
