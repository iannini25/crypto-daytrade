"""Cost model for the desk.

Cash fees are Bybit spot VIP0: 0.10% per side, 0.20% round trip.
The gate adds 0.10% slippage, so the round-trip cost is 0.30%.

Net R:R uses percent of entry, not the raw price ratio:

    net_rr = (target% - 0.30) / (stop% + 0.30)

which is the same requirement as target% >= 2 * stop% + 3 * 0.30.

Quote-fee cash model (ledger debits, slippage not included):

- entry debit  = qty * entry * (1 + fee)
- exit credit  = qty * exit  * (1 - fee)
- flat exit == entry loses exactly qty * entry * 2 * fee  (0.20%)
"""

from __future__ import annotations

from decimal import Decimal

# Per side. Do not lower this to make a setup look tradable.
VIP0_SIDE_FEE = Decimal("0.001")
# 0.10% + 0.10% fees.
ROUND_TRIP_FEE = Decimal("0.002")
# Extra 0.10% slippage budget on the round trip. Not a live fill.
SLIPPAGE_ROUND_TRIP = Decimal("0.001")
# 0.20% fees + 0.10% slippage.
ROUND_TRIP_COST = Decimal("0.003")
# Same cost in percent points, the unit the net R:R formula uses.
COST_PERCENT = Decimal("0.30")
# Cost must be at most 10% of the stop distance, so the stop is at least 3.0%.
MIN_STOP_PERCENT = COST_PERCENT / Decimal("0.10")


def as_decimal(value: Decimal | int | str) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def net_loss_per_unit(entry: Decimal, stop: Decimal, fee_rate: Decimal = VIP0_SIDE_FEE) -> Decimal:
    """Quote lost per one base unit if a long is stopped, including both fees."""
    entry = as_decimal(entry)
    stop = as_decimal(stop)
    fee_rate = as_decimal(fee_rate)
    return (entry - stop) + fee_rate * (entry + stop)


def net_gain_per_unit(entry: Decimal, target: Decimal, fee_rate: Decimal = VIP0_SIDE_FEE) -> Decimal:
    """Quote gained per one base unit if a long hits the target, after both fees."""
    entry = as_decimal(entry)
    target = as_decimal(target)
    fee_rate = as_decimal(fee_rate)
    return (target - entry) - fee_rate * (entry + target)


def gross_rr(entry: Decimal, stop: Decimal, target: Decimal) -> Decimal:
    """Reward/risk ignoring fees. Kept so the fee drag is visible next to it."""
    entry = as_decimal(entry)
    stop = as_decimal(stop)
    target = as_decimal(target)
    risk = entry - stop
    if risk <= 0:
        raise ValueError("stop must be below entry")
    return (target - entry) / risk


def stop_percent(entry: Decimal, stop: Decimal) -> Decimal:
    """Stop distance as percent of entry. 3.5 means 3.5%."""
    entry = as_decimal(entry)
    stop = as_decimal(stop)
    if entry <= 0:
        raise ValueError("entry must be positive")
    return (entry - stop) / entry * Decimal("100")


def target_percent(entry: Decimal, target: Decimal) -> Decimal:
    """Target distance as percent of entry. 7.9 means 7.9%."""
    entry = as_decimal(entry)
    target = as_decimal(target)
    if entry <= 0:
        raise ValueError("entry must be positive")
    return (target - entry) / entry * Decimal("100")


def minimum_target_percent(stop_pct: Decimal, cost_percent: Decimal = COST_PERCENT) -> Decimal:
    """Smallest target% that still prints net R:R of 2. Equals 2*stop + 3*cost."""
    return as_decimal(stop_pct) * Decimal("2") + as_decimal(cost_percent) * Decimal("3")


def net_rr(entry: Decimal, stop: Decimal, target: Decimal, cost_percent: Decimal = COST_PERCENT) -> Decimal:
    """(target% - cost%) / (stop% + cost%). The gate's net R:R. Cost default is 0.30."""
    stop_pct = stop_percent(entry, stop)
    gained = target_percent(entry, target)
    denominator = stop_pct + as_decimal(cost_percent)
    if denominator <= 0:
        raise ValueError("net risk percent must be positive")
    return (gained - as_decimal(cost_percent)) / denominator


def cost_percent_points(fee_rate: Decimal = VIP0_SIDE_FEE) -> Decimal:
    """Round-trip cost in percent points. VIP0 plus 0.10 slippage is 0.30."""
    fee_rate = as_decimal(fee_rate)
    return (fee_rate * Decimal("2") + SLIPPAGE_ROUND_TRIP) * Decimal("100")


def round_trip_pnl(entry: Decimal, exit_price: Decimal, qty: Decimal, fee_rate: Decimal = VIP0_SIDE_FEE) -> Decimal:
    """Realized quote PnL for a long opened and closed at the given prices."""
    entry = as_decimal(entry)
    exit_price = as_decimal(exit_price)
    qty = as_decimal(qty)
    fee_rate = as_decimal(fee_rate)
    debit = qty * entry * (Decimal("1") + fee_rate)
    credit = qty * exit_price * (Decimal("1") - fee_rate)
    return credit - debit


def expectancy(net_reward: Decimal, net_risk: Decimal, win_rate: Decimal) -> Decimal:
    """Expected quote result per unit given a win rate and fee-adjusted outcomes."""
    net_reward = as_decimal(net_reward)
    net_risk = as_decimal(net_risk)
    win_rate = as_decimal(win_rate)
    return win_rate * net_reward - (Decimal("1") - win_rate) * net_risk


def breakeven_win_rate(reward_risk: Decimal) -> Decimal:
    """Win rate that zeroes expectancy at a given fee-adjusted R multiple."""
    reward_risk = as_decimal(reward_risk)
    if reward_risk <= 0:
        raise ValueError("R:R must be positive")
    return Decimal("1") / (Decimal("1") + reward_risk)
