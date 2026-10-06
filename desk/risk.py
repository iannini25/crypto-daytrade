"""Risk gate.

Hard rules (environment may only tighten these; see config.py):

- spot, long only, at most one open position
- round-trip cost 0.30% (0.20% VIP0 + 0.10% slippage)
- net R:R = (target% - 0.30) / (stop% + 0.30) >= 2
- stop at least 3.0% so that 0.30% cost is at most 10% of the risk distance
- on a ~19.9 USDT book the 6 USDT minimum order puts the stop in bands:
  <= ~3.02% is the 1% target zone, through ~9.65% needs justification, above that rejects
- kill switch at or below 90% of starting equity
- no new entry after one losing trade on the same Sao Paulo day
- stops anchor on a 1h or daily swing; 3xATR(D) is only a ceiling

This module never sends an order.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, ROUND_DOWN, ROUND_HALF_UP

from desk.fees import (
    COST_PERCENT,
    MIN_STOP_PERCENT,
    VIP0_SIDE_FEE,
    cost_percent_points,
    net_rr,
    stop_percent,
    target_percent,
)

QTY_STEP = Decimal("0.00000001")

MIN_RR = Decimal("2")
TARGET_RISK = Decimal("0.01")
RISK_CAP = Decimal("0.03")
KILL_RATIO = Decimal("0.90")
MIN_ORDER_USDT = Decimal("6")
REFERENCE_EQUITY = Decimal("19.9")


@dataclass(frozen=True)
class OrderPlan:
    symbol: str
    entry: Decimal
    stop: Decimal
    target: Decimal
    side: str = "Buy"
    category: str = "spot"
    # "1h" or "D". A 15m swing is not a valid anchor.
    stop_anchor: str = "1h"
    # Price distance of 3x daily ATR. None skips the ceiling check.
    atr_ceiling: Decimal | None = None


@dataclass(frozen=True)
class AccountSnapshot:
    equity: Decimal = REFERENCE_EQUITY
    starting_equity: Decimal = REFERENCE_EQUITY
    open_positions: int = 0
    fee_rate: Decimal = VIP0_SIDE_FEE
    max_risk: Decimal = TARGET_RISK
    risk_cap: Decimal = RISK_CAP
    kill_ratio: Decimal = KILL_RATIO
    min_rr: Decimal = MIN_RR
    max_positions: int = 1
    min_order_usdt: Decimal = MIN_ORDER_USDT
    losses_today: int = 0


@dataclass(frozen=True)
class StopBands:
    """Stop-width bands for this equity, in percent points (3.5 means 3.5%)."""

    min_stop_percent: Decimal
    target_zone_max_percent: Decimal
    cap_stop_percent: Decimal
    cost_percent: Decimal
    min_order_usdt: Decimal
    equity: Decimal

    def label_for(self, stop_pct: Decimal) -> tuple[str, str]:
        """Return (band id, human label). Band id is stable for tests."""
        if stop_pct < self.min_stop_percent:
            return (
                "cost_reject",
                (
                    f"cost rule: stop { _pct(stop_pct) }% is under the "
                    f"{_pct(self.min_stop_percent)}% minimum "
                    f"({_pct(self.cost_percent)}% round trip must be <= 10% of the stop)"
                ),
            )
        if stop_pct <= self.target_zone_max_percent:
            return (
                "target_1pct",
                (
                    f"1% target zone (stop {_pct(stop_pct)}%; "
                    f"zone <= {_pct(self.target_zone_max_percent)}%; "
                    f"exception through {_pct(self.cap_stop_percent)}%)"
                ),
            )
        if stop_pct <= self.cap_stop_percent:
            return (
                "exception",
                (
                    f"exception, needs justification (stop {_pct(stop_pct)}%; "
                    f"1% zone <= {_pct(self.target_zone_max_percent)}%; "
                    f"cap {_pct(self.cap_stop_percent)}%)"
                ),
            )
        return (
            "account_cap",
            (
                f"account cap: stop {_pct(stop_pct)}% is above {_pct(self.cap_stop_percent)}% "
                f"(min order {self.min_order_usdt} USDT would risk more than 3% of equity)"
            ),
        )


@dataclass(frozen=True)
class GateDecision:
    allowed: bool
    reasons: tuple[str, ...]
    qty: Decimal
    hypothetical_qty: Decimal
    risk_fraction: Decimal
    rr_after_fees: Decimal | None
    gross_rr: Decimal | None
    net_risk_per_unit: Decimal | None
    net_reward_per_unit: Decimal | None
    notional: Decimal
    cash_limited: bool
    stop_percent: Decimal | None = None
    target_percent: Decimal | None = None
    stop_band: str = "n/a"
    band_label: str = ""
    min_stop_percent: Decimal = MIN_STOP_PERCENT
    target_zone_max_percent: Decimal | None = None
    cap_stop_percent: Decimal | None = None
    cost_percent: Decimal = COST_PERCENT

    @property
    def summary(self) -> str:
        band = self.band_label
        if self.allowed:
            if band:
                return f"allowed; {band}"
            return "allowed"
        text = "; ".join(self.reasons)
        if band and band not in text:
            return f"{text}; {band}"
        return text


def _pct(value: Decimal) -> str:
    rounded = value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return format(rounded, "f")


def stop_bands(
    equity: Decimal,
    *,
    fee_rate: Decimal = VIP0_SIDE_FEE,
    min_order_usdt: Decimal = MIN_ORDER_USDT,
    target_risk: Decimal = TARGET_RISK,
    risk_cap: Decimal = RISK_CAP,
) -> StopBands:
    """Band edges from the min order and this equity.

    A 6 USDT order on 19.9 USDT equity risks about 1% of equity at a ~3.02% stop
    and about 3% of equity at a ~9.65% stop (0.30% round-trip cost included).
    """
    cost_pct = cost_percent_points(fee_rate)
    cost_frac = cost_pct / Decimal("100")

    def edge(risk: Decimal) -> Decimal:
        raw = (risk * equity / min_order_usdt - cost_frac) * Decimal("100")
        return raw.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    min_stop = (cost_pct / Decimal("0.10")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return StopBands(
        min_stop_percent=min_stop,
        target_zone_max_percent=edge(target_risk),
        cap_stop_percent=edge(risk_cap),
        cost_percent=cost_pct,
        min_order_usdt=min_order_usdt,
        equity=equity,
    )


def _prices_ok(plan: OrderPlan) -> bool:
    return (
        plan.entry > 0
        and plan.stop > 0
        and plan.target > 0
        and plan.stop < plan.entry < plan.target
    )


def _floor_qty(qty: Decimal) -> Decimal:
    if qty <= 0:
        return Decimal("0")
    return qty.quantize(QTY_STEP, rounding=ROUND_DOWN)


def evaluate(
    plan: OrderPlan,
    account: AccountSnapshot,
    requested_qty: Decimal | None = None,
    *,
    now: datetime | None = None,
    events: tuple = (),
    entry_locked: bool = False,
    entry_lock_reason: str = "",
) -> GateDecision:
    """Return whether a long spot plan may be paper-sized. Never sends an order.

    Clock rules (session, event lock) run only when `now` or `entry_locked` is set,
    so a pure cost check does not depend on the wall clock.
    """
    reasons: list[str] = []
    bands = stop_bands(
        account.equity,
        fee_rate=account.fee_rate,
        min_order_usdt=account.min_order_usdt,
        target_risk=account.max_risk,
        risk_cap=account.risk_cap,
    )

    if plan.category != "spot":
        reasons.append("spot only; category must be spot")
    if plan.side != "Buy":
        reasons.append("long-only; side must be Buy")
    if not plan.symbol.endswith("USDT") or not plan.symbol.isalnum():
        reasons.append("symbol must be a USDT spot pair")
    if account.equity <= 0 or account.starting_equity <= 0:
        reasons.append("equity must be positive")
    if account.equity <= account.starting_equity * account.kill_ratio:
        reasons.append("kill switch: equity <= 90% of starting equity")
    if account.open_positions >= account.max_positions:
        reasons.append("max 1 open position")
    if account.losses_today >= 1:
        reasons.append("loss lock: one losing trade already today; no new entries")
    if account.fee_rate < VIP0_SIDE_FEE:
        reasons.append("fee rate below VIP0 0.10% per side")
    if plan.stop_anchor not in {"1h", "D"}:
        reasons.append("stop must anchor on 1h or daily swing structure, not a 15m swing")
    if now is not None and not entry_locked:
        from desk.events import entry_lock

        lock_reason = entry_lock(now, events)
        if lock_reason:
            entry_locked = True
            entry_lock_reason = lock_reason
    if entry_locked:
        reasons.append(entry_lock_reason or "event lock: no new entries")
    if now is not None:
        from desk.session import in_liquidity_window

        if not in_liquidity_window(now):
            reasons.append("outside 10:00-12:30 America/Sao_Paulo; no new entry")
    if not _prices_ok(plan):
        reasons.append("need 0 < stop < entry < target")

    stop_pct: Decimal | None = None
    gained_pct: Decimal | None = None
    band_id = "n/a"
    band_label = ""
    rr: Decimal | None = None
    gross: Decimal | None = None
    hypothetical = Decimal("0")
    cash_limited = False
    cost_pct = bands.cost_percent
    cost_frac = cost_pct / Decimal("100")

    if _prices_ok(plan) and account.fee_rate >= VIP0_SIDE_FEE:
        stop_pct = stop_percent(plan.entry, plan.stop)
        gained_pct = target_percent(plan.entry, plan.target)
        band_id, band_label = bands.label_for(stop_pct)
        gross_risk = plan.entry - plan.stop
        gross = (plan.target - plan.entry) / gross_risk
        rr = net_rr(plan.entry, plan.stop, plan.target, cost_pct)
        if band_id == "cost_reject":
            reasons.append(band_label)
        elif band_id == "account_cap":
            reasons.append(band_label)
        if plan.atr_ceiling is not None and (plan.entry - plan.stop) > plan.atr_ceiling:
            reasons.append("stop is wider than the 3xATR(D) ceiling; ATR is not itself a stop")
        if rr < account.min_rr:
            reasons.append("net R:R < 2")
        risk_per_notional = (stop_pct / Decimal("100")) + cost_frac
        if risk_per_notional <= 0:
            reasons.append("non-positive net risk after costs")
        else:
            notional_target = (account.equity * account.max_risk) / risk_per_notional
            cash_notional = account.equity / (Decimal("1") + account.fee_rate)
            if cash_notional < account.min_order_usdt:
                reasons.append("cash below min order 6 USDT")
                chosen = Decimal("0")
            elif notional_target >= account.min_order_usdt:
                chosen = notional_target
                cash_limited = False
            else:
                chosen = account.min_order_usdt
                cash_limited = False
            if chosen > cash_notional:
                chosen = cash_notional
                cash_limited = True
            if requested_qty is not None:
                requested_notional = requested_qty * plan.entry
                if requested_notional < account.min_order_usdt:
                    reasons.append("requested qty is below the 6 USDT min order")
                    chosen = Decimal("0")
                elif requested_notional * risk_per_notional > account.equity * account.risk_cap:
                    reasons.append("requested qty risks more than 3% of equity")
                    chosen = Decimal("0")
                elif (
                    band_id == "target_1pct"
                    and requested_notional * risk_per_notional > account.equity * account.max_risk
                ):
                    reasons.append("requested qty risks more than the 1% target")
                    chosen = Decimal("0")
                else:
                    chosen = min(requested_notional, cash_notional)
                    cash_limited = requested_notional > cash_notional
            hypothetical = _floor_qty(chosen / plan.entry) if chosen > 0 else Decimal("0")
            if hypothetical <= 0 and "cash below min order 6 USDT" not in reasons:
                if not any(reason.startswith("requested qty") for reason in reasons):
                    reasons.append("sized quantity is zero")

    blocked_hard = any(
        reason.startswith("kill switch")
        or reason.startswith("max 1")
        or reason.startswith("spot only")
        or reason.startswith("long-only")
        or reason.startswith("equity must")
        or reason.startswith("fee rate below")
        or reason.startswith("loss lock")
        or reason.startswith("event lock")
        or reason.startswith("outside 10:00")
        for reason in reasons
    )
    if blocked_hard:
        hypothetical = Decimal("0")

    qty = Decimal("0") if reasons else hypothetical
    notional = qty * plan.entry if qty > 0 else Decimal("0")
    risk_fraction = Decimal("0")
    if qty > 0 and stop_pct is not None and account.equity > 0:
        risk_per_notional = (stop_pct / Decimal("100")) + cost_frac
        risk_fraction = (notional * risk_per_notional) / account.equity
        if risk_fraction > account.risk_cap:
            reasons.append("risk fraction exceeds the 3% cap")
            qty = Decimal("0")
            notional = Decimal("0")
            risk_fraction = Decimal("0")

    # Dollar risk and reward per base unit under the percent cost model,
    # so callers can still show a cash figure next to the ratio.
    net_risk = None
    net_reward = None
    if stop_pct is not None and gained_pct is not None:
        net_risk = plan.entry * (stop_pct + cost_pct) / Decimal("100")
        net_reward = plan.entry * (gained_pct - cost_pct) / Decimal("100")

    return GateDecision(
        allowed=not reasons,
        reasons=tuple(dict.fromkeys(reasons)),
        qty=qty,
        hypothetical_qty=hypothetical if not blocked_hard else Decimal("0"),
        risk_fraction=risk_fraction,
        rr_after_fees=rr,
        gross_rr=gross,
        net_risk_per_unit=net_risk,
        net_reward_per_unit=net_reward,
        notional=notional,
        cash_limited=cash_limited and not reasons,
        stop_percent=stop_pct,
        target_percent=gained_pct,
        stop_band=band_id,
        band_label=band_label,
        min_stop_percent=bands.min_stop_percent,
        target_zone_max_percent=bands.target_zone_max_percent,
        cap_stop_percent=bands.cap_stop_percent,
        cost_percent=cost_pct,
    )
