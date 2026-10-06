"""Dry-run scanner.

Combines the daily HH/HL filter, a 15m pattern label, the Sao Paulo window,
and the fee-aware risk gate. The result is a disposition word for a person.

This module does not import the order helper and does not write the ledger.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from desk.bybit import Candle
from desk.patterns import MIN_HEIGHT, classify, daily_hh_hl
from desk.risk import AccountSnapshot, OrderPlan, evaluate
from desk.session import in_liquidity_window


@dataclass(frozen=True)
class ScanRow:
    symbol: str
    in_window: bool
    daily_hh_hl: bool
    pattern: str | None
    height_pct: Decimal | None
    close_confirmed: bool
    rr_after_fees: Decimal | None
    gross_rr: Decimal | None
    disposition: str
    notes: tuple[str, ...]


def analyze(
    symbol: str,
    daily: list[Candle],
    m15: list[Candle],
    account: AccountSnapshot,
    now: datetime,
) -> ScanRow:
    notes: list[str] = []
    window = in_liquidity_window(now)
    if not window:
        notes.append("outside 10:00–12:30 America/Sao_Paulo; watch only")
    trend = daily_hh_hl(daily)
    if not trend:
        notes.append("daily filter missing HH/HL; long continuation is off")
    match = classify(m15)
    if match is None:
        notes.append("no playbook pattern on closed 15m bars")
        return ScanRow(
            symbol=symbol,
            in_window=window,
            daily_hh_hl=trend,
            pattern=None,
            height_pct=None,
            close_confirmed=False,
            rr_after_fees=None,
            gross_rr=None,
            disposition="ignore",
            notes=tuple(notes),
        )

    notes.append(f"pattern {match.name}")
    if match.height_pct < MIN_HEIGHT:
        notes.append("height < 1%; use 1h structure; not a 15m trigger")
    if not match.confirmed:
        notes.append("15m close has not cleared resistance")

    entry = match.resistance if not match.confirmed else m15[-1].close
    plan = OrderPlan(
        symbol=symbol,
        entry=entry,
        stop=match.support,
        target=match.target,
        side="Buy",
        category="spot",
    )
    # Preview the fee math even when the session or the daily filter blocks it.
    # Open-position / kill state still comes from the real account snapshot,
    # but a flat reference account is used when we only want the pattern math
    # and the live account is already full. Both are reported.
    preview_account = AccountSnapshot(
        equity=account.equity,
        starting_equity=account.starting_equity,
        open_positions=0,
        fee_rate=account.fee_rate,
        max_risk=account.max_risk,
        kill_ratio=account.kill_ratio,
        min_rr=account.min_rr,
    )
    preview = evaluate(plan, preview_account)
    live = evaluate(plan, account)
    if preview.rr_after_fees is not None and preview.rr_after_fees < account.min_rr:
        notes.append("R:R after the 0.20% round trip is below 2")
    if not live.allowed and live.summary != preview.summary:
        notes.append(f"account gate: {live.summary}")
    elif not preview.allowed:
        notes.append(f"fee gate: {preview.summary}")

    disposition = "ignore"
    if not trend:
        disposition = "ignore"
    elif match.height_pct < MIN_HEIGHT:
        disposition = "watch"
    elif not match.confirmed or not window or not preview.allowed or not live.allowed:
        disposition = "watch"
    else:
        disposition = "paper_candidate"
        notes.append("paper candidate for a human to review; no order sent")

    return ScanRow(
        symbol=symbol,
        in_window=window,
        daily_hh_hl=trend,
        pattern=match.name,
        height_pct=match.height_pct,
        close_confirmed=match.confirmed,
        rr_after_fees=preview.rr_after_fees,
        gross_rr=preview.gross_rr,
        disposition=disposition,
        notes=tuple(notes),
    )
