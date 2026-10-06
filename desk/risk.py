"""Risk gate.

Hard rules (environment may only tighten these; see config.py):

- spot category
- long only (side Buy)
- at most 1 open position
- at most 1% of equity at risk after fees
- no new risk when equity is at or below 90% of starting equity
- reward:risk after fees at least 2
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_DOWN

from desk.fees import VIP0_SIDE_FEE, net_gain_per_unit, net_loss_per_unit

QTY_STEP = Decimal("0.00000001")

MIN_RR = Decimal("2")
MAX_RISK = Decimal("0.01")
KILL_RATIO = Decimal("0.90")


@dataclass(frozen=True)
class OrderPlan:
    symbol: str
    entry: Decimal
    stop: Decimal
    target: Decimal
    side: str = "Buy"
    category: str = "spot"


@dataclass(frozen=True)
class AccountSnapshot:
    equity: Decimal
    starting_equity: Decimal
    open_positions: int = 0
    fee_rate: Decimal = VIP0_SIDE_FEE
    max_risk: Decimal = MAX_RISK
    kill_ratio: Decimal = KILL_RATIO
    min_rr: Decimal = MIN_RR
    max_positions: int = 1


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

    @property
    def summary(self) -> str:
        if self.allowed:
            return "allowed"
        return "; ".join(self.reasons)


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


def evaluate(plan: OrderPlan, account: AccountSnapshot, requested_qty: Decimal | None = None) -> GateDecision:
    """Return whether a long spot plan may be paper-sized. Never sends an order."""
    reasons: list[str] = []

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
    if account.fee_rate < VIP0_SIDE_FEE:
        reasons.append("fee rate below VIP0 0.10% per side")
    if not _prices_ok(plan):
        reasons.append("need 0 < stop < entry < target")

    net_risk: Decimal | None = None
    net_reward: Decimal | None = None
    rr: Decimal | None = None
    gross: Decimal | None = None
    hypothetical = Decimal("0")
    cash_limited = False

    if _prices_ok(plan):
        gross_risk = plan.entry - plan.stop
        gross = (plan.target - plan.entry) / gross_risk
        net_risk = net_loss_per_unit(plan.entry, plan.stop, account.fee_rate)
        net_reward = net_gain_per_unit(plan.entry, plan.target, account.fee_rate)
        if net_risk <= 0:
            reasons.append("non-positive net risk after fees")
        else:
            rr = net_reward / net_risk
            if net_reward <= 0 or rr < account.min_rr:
                reasons.append("R:R after fees < 2")
            risk_qty = (account.equity * account.max_risk) / net_risk
            unit_cost = plan.entry * (Decimal("1") + account.fee_rate)
            cash_qty = account.equity / unit_cost
            hypothetical = _floor_qty(min(risk_qty, cash_qty))
            cash_limited = cash_qty < risk_qty
            if requested_qty is not None and requested_qty > risk_qty:
                reasons.append("requested qty risks more than 1% after fees")
                hypothetical = Decimal("0")
            elif requested_qty is not None:
                hypothetical = _floor_qty(min(requested_qty, cash_qty))
                cash_limited = requested_qty > cash_qty
            if hypothetical <= 0:
                reasons.append("sized quantity is zero")

    blocked_hard = any(
        reason.startswith("kill switch")
        or reason.startswith("max 1")
        or reason.startswith("spot only")
        or reason.startswith("long-only")
        or reason.startswith("equity must")
        or reason.startswith("fee rate below")
        for reason in reasons
    )
    if blocked_hard:
        hypothetical = Decimal("0")

    qty = Decimal("0") if reasons else hypothetical
    notional = qty * plan.entry if qty > 0 else Decimal("0")
    if qty > 0 and net_risk is not None and account.equity > 0:
        risk_fraction = (qty * net_risk) / account.equity
    else:
        risk_fraction = Decimal("0")
    if risk_fraction > account.max_risk:
        reasons.append("risk fraction exceeds 1%")
        qty = Decimal("0")
        notional = Decimal("0")
        risk_fraction = Decimal("0")

    return GateDecision(
        allowed=not reasons,
        reasons=tuple(reasons),
        qty=qty,
        hypothetical_qty=hypothetical if not blocked_hard else Decimal("0"),
        risk_fraction=risk_fraction,
        rr_after_fees=rr,
        gross_rr=gross,
        net_risk_per_unit=net_risk,
        net_reward_per_unit=net_reward,
        notional=notional,
        cash_limited=cash_limited and not reasons,
    )
