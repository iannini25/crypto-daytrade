"""Dry-run scanner.

Daily HH/HL and a close above SMA100 filter the long. The stop is the latest
1h or daily swing low, capped by 3x daily ATR. The 15m close only times the
entry, and only inside 10:00–12:30 America/Sao_Paulo.

This module does not import the order helper and does not write the ledger.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from desk.bybit import Candle
from desk.events import MacroEvent, entry_lock
from desk.patterns import classify, daily_hh_hl
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
    trend = daily_hh_hl(daily)
    if not trend:
        notes.append("daily filter missing HH/HL; long continuation is off")
    sma_value = sma(daily)
    trend_average = above_sma100(daily)
    if sma_value is None:
        notes.append("need 100 closed daily bars for SMA100")
    elif not trend_average:
        notes.append("daily close is not above SMA100")

    match = classify(m15) if len(m15) >= 15 else None
    if match is None:
        notes.append("no playbook pattern on closed 15m bars; nothing to time")
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
            "ignore",
            notes,
        )

    notes.append(f"15m timing label {match.name}; stop is not taken from this box")
    if not match.confirmed:
        notes.append("15m close has not cleared resistance")
    entry = m15[-1].close if match.confirmed else match.resistance
    anchored = structure_stop(hourly, daily, entry)
    ceiling = atr_ceiling(daily)
    if anchored is None:
        notes.append("no 1h or daily swing low under the entry; a 15m swing is not a stop")
        return _row(
            symbol,
            window,
            trend,
            trend_average,
            match.name,
            match.height_pct,
            match.confirmed,
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
        target=match.target,
        side="Buy",
        category="spot",
        stop_anchor=anchor_name,
        atr_ceiling=ceiling,
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

    filters_ok = trend and trend_average and match.confirmed and window and lock is None and account.losses_today == 0
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
        match.name,
        match.height_pct,
        match.confirmed,
        anchor_name,
        preview.stop_band,
        preview.rr_after_fees,
        preview.gross_rr,
        disposition,
        notes,
    )


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
