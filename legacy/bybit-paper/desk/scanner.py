"""Dry-run scanner.

Daily HH/HL and a close above SMA100 filter the long. The pattern itself is
drawn on the 1h or the daily chart. The stop is that structure, inside
3.0–9.66% and at or under 3x daily ATR. The 15m close only confirms the
entry, and only inside 10:00–12:30 America/Sao_Paulo. Active patterns are
long-only. Exit-only names never become a long or a short.

This module does not import the order helper and does not write the ledger.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from desk.bybit import Candle
from desk.events import MacroEvent, entry_lock
from desk.patterns import daily_hh_hl, detect, long_entry_allowed, pattern_role
from desk.risk import AccountSnapshot, OrderPlan, evaluate
from desk.session import in_liquidity_window
from desk.structure import above_sma100, atr_ceiling, sma, structure_stop


@dataclass(frozen=True)
class ScanRow:
    symbol: str
    in_window: bool
    daily_hh_hl: bool
    above_sma100: bool
    pattern: str | None
    height_pct: Decimal | None
    close_confirmed: bool
    stop_anchor: str | None
    stop_band: str
    rr_after_fees: Decimal | None
    gross_rr: Decimal | None
    disposition: str
    notes: tuple[str, ...]


def analyze(
    symbol: str,
    daily: list[Candle],
    hourly: list[Candle],
    m15: list[Candle],
    account: AccountSnapshot,
    now: datetime,
    events: tuple[MacroEvent, ...] = (),
) -> ScanRow:
    notes: list[str] = []
    window = in_liquidity_window(now)
    if not window:
        notes.append("outside 10:00-12:30 America/Sao_Paulo; 15m close is not an entry")
    lock = entry_lock(now, events)
    if lock:
        notes.append(lock)
    if account.losses_today >= 1:
        notes.append("loss lock: one losing trade already today; no new entries")
    if account.trades_today >= account.max_trades_per_day:
        notes.append("trade cap: 3 trades already today; no new entries")
    trend = daily_hh_hl(daily)
    if not trend:
        notes.append("daily filter missing HH/HL; long continuation is off")
    sma_value = sma(daily)
    trend_average = above_sma100(daily)
    if sma_value is None:
        notes.append("need 100 closed daily bars for SMA100")
    elif not trend_average:
        notes.append("daily close is not above SMA100")

    drawn = _pattern_on_1h_or_daily(hourly, daily)
    if drawn is None:
        notes.append("no active pattern on 1h or daily; 15m only confirms a close")
        return _row(
            symbol,
            window,
            trend,
            trend_average,
            None,
            None,
            False,
            None,
            "n/a",
            None,
            None,
            "watch" if trend else "ignore",
            notes,
        )

    match, entry_tf, role = drawn
    if role == "exit_only":
        notes.append(
            f"{entry_tf} {match.name} is exit-only: never open a short and never open a new long"
        )
        return _row(
            symbol,
            window,
            trend,
            trend_average,
            match.name,
            match.height_pct,
            False,
            None,
            "n/a",
            None,
            None,
            "exit_only",
            notes,
        )
    if role != "active":
        notes.append(f"{entry_tf} {match.name} is outside playbook v1; not a paper entry")
        return _row(
            symbol,
            window,
            trend,
            trend_average,
            match.name,
            match.height_pct,
            False,
            None,
            "n/a",
            None,
            None,
            "watch" if trend else "ignore",
            notes,
        )

    entry_name = match.name
    entry_target = match.target
    if not m15:
        notes.append("no 15m close; the pattern is on 1h/D and 15m only confirms")
        close_confirmed = False
        entry = match.resistance
    else:
        close_confirmed = m15[-1].close > match.resistance
        entry = m15[-1].close if close_confirmed else match.resistance
        if close_confirmed:
            notes.append(
                f"{entry_tf} {entry_name} confirmed by a 15m close; the 15m chart does not draw the pattern"
            )
        else:
            notes.append("15m close has not cleared the 1h/D level")
    anchored = structure_stop(hourly, daily, entry)
    ceiling = atr_ceiling(daily)
    if anchored is None:
        notes.append("no 1h or daily swing low under the entry; a 15m swing is not a stop")
        return _row(
            symbol,
            window,
            trend,
            trend_average,
            entry_name,
            match.height_pct,
            close_confirmed,
            None,
            "n/a",
            None,
            None,
            "watch" if trend else "ignore",
            notes,
        )

    stop, anchor_name = anchored
    notes.append(f"stop anchor {anchor_name} swing low")
    if ceiling is None:
        notes.append("3xATR(D) ceiling unavailable")
    plan = OrderPlan(
        symbol=symbol,
        entry=entry,
        stop=stop,
        target=entry_target,
        side="Buy",
        category="spot",
        stop_anchor=anchor_name,
        atr_ceiling=ceiling,
        pattern=entry_name,
        pattern_timeframe=entry_tf,
        pattern_low=stop,
    )
    preview_account = AccountSnapshot(
        equity=account.equity,
        starting_equity=account.starting_equity,
        open_positions=0,
        fee_rate=account.fee_rate,
        max_risk=account.max_risk,
        risk_cap=account.risk_cap,
        kill_ratio=account.kill_ratio,
        min_rr=account.min_rr,
        min_order_usdt=account.min_order_usdt,
        losses_today=0,
    )
    preview = evaluate(plan, preview_account, now=now, entry_locked=lock is not None, entry_lock_reason=lock or "")
    live = evaluate(
        plan,
        account,
        now=now,
        entry_locked=lock is not None,
        entry_lock_reason=lock or "",
    )
    if preview.band_label:
        notes.append(preview.band_label)
    if preview.rr_after_fees is not None and preview.rr_after_fees < account.min_rr:
        notes.append("net R:R after the 0.30% round trip is below 2")
    if not live.allowed and live.summary != preview.summary:
        notes.append(f"account gate: {live.summary}")

    filters_ok = (
        trend
        and trend_average
        and close_confirmed
        and window
        and lock is None
        and account.losses_today == 0
        and account.trades_today < account.max_trades_per_day
        and long_entry_allowed(entry_name, entry_tf or "")
    )
    if not trend:
        disposition = "ignore"
    elif filters_ok and preview.allowed and live.allowed:
        disposition = "paper_candidate"
        notes.append("paper candidate for a human to review; no order sent")
    else:
        disposition = "watch"

    return _row(
        symbol,
        window,
        trend,
        trend_average,
        entry_name,
        match.height_pct,
        close_confirmed,
        anchor_name,
        preview.stop_band,
        preview.rr_after_fees,
        preview.gross_rr,
        disposition,
        notes,
    )


def _pattern_on_1h_or_daily(hourly: list[Candle], daily: list[Candle]):
    """Pattern drawn on 1h, otherwise on the daily chart.

    An exit-only name on either timeframe vetoes a new long. The 15m series
    is not consulted: it only confirms a close.
    """
    exit_hit = None
    active_hit = None
    other = None
    for series, timeframe in ((hourly, "1h"), (daily, "D")):
        found = detect(series) if len(series) >= 15 else None
        if found is None:
            continue
        role = pattern_role(found.name)
        if role == "exit_only" and exit_hit is None:
            exit_hit = (found, timeframe, role)
        elif long_entry_allowed(found.name, timeframe) and active_hit is None:
            active_hit = (found, timeframe, role)
        elif other is None:
            other = (found, timeframe, role)
    return exit_hit or active_hit or other


def _row(
    symbol: str,
    window: bool,
    trend: bool,
    trend_average: bool,
    pattern: str | None,
    height: Decimal | None,
    confirmed: bool,
    anchor: str | None,
    band: str,
    net_rr: Decimal | None,
    gross: Decimal | None,
    disposition: str,
    notes: list[str],
) -> ScanRow:
    return ScanRow(
        symbol=symbol,
        in_window=window,
        daily_hh_hl=trend,
        above_sma100=trend_average,
        pattern=pattern,
        height_pct=height,
        close_confirmed=confirmed,
        stop_anchor=anchor,
        stop_band=band,
        rr_after_fees=net_rr,
        gross_rr=gross,
        disposition=disposition,
        notes=tuple(notes),
    )
