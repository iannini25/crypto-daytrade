"""VIP0 spot fee accounting.

Bybit spot VIP0 is 0.10% maker and 0.10% taker. This desk assumes a taker
fill on the way in and on the way out, so the headline round trip is 0.20%.

Quote-fee model (exact flat round trip, no hidden fee-on-fee):

- entry debit  = qty * entry * (1 + fee)
- exit credit  = qty * exit  * (1 - fee)
- flat exit == entry loses exactly qty * entry * 2 * fee
"""

from __future__ import annotations

from decimal import Decimal

# Per side. Do not lower this to make a setup look tradable.
VIP0_SIDE_FEE = Decimal("0.001")
# 0.10% + 0.10%.
ROUND_TRIP_FEE = Decimal("0.002")


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


def net_rr(entry: Decimal, stop: Decimal, target: Decimal, fee_rate: Decimal = VIP0_SIDE_FEE) -> Decimal:
    """Reward/risk after entry and exit fees. This is the number the gate uses."""
    risk = net_loss_per_unit(entry, stop, fee_rate)
    if risk <= 0:
        raise ValueError("net risk must be positive")
    return net_gain_per_unit(entry, target, fee_rate) / risk


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
