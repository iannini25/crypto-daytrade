"""Risk gate: 1% risk, one position, kill at 90%, R:R after fees >= 2."""

from decimal import Decimal

import pytest

from desk.config import ConfigError, load_config
from desk.risk import AccountSnapshot, OrderPlan, evaluate


def _plan(**overrides) -> OrderPlan:
    fields = dict(
        symbol="BTCUSDT",
        entry=Decimal("100"),
        stop=Decimal("98"),
        target=Decimal("110"),
    )
    fields.update(overrides)
    return OrderPlan(**fields)


def _account(**overrides) -> AccountSnapshot:
    fields = dict(equity=Decimal("20"), starting_equity=Decimal("20"), open_positions=0)
    fields.update(overrides)
    return AccountSnapshot(**fields)


def test_sized_qty_risks_at_most_one_percent():
    decision = evaluate(_plan(), _account())
    assert decision.allowed
    assert decision.risk_fraction <= Decimal("0.01")
    assert decision.risk_fraction > Decimal("0.009")
    assert decision.rr_after_fees > Decimal("2")
    assert decision.qty > 0
    assert decision.notional == decision.qty * Decimal("100")


def test_gross_two_r_is_rejected_after_fees():
    decision = evaluate(
        _plan(entry=Decimal("100"), stop=Decimal("99"), target=Decimal("102")),
        _account(),
    )
    assert not decision.allowed
    assert decision.gross_rr == Decimal("2")
    assert decision.rr_after_fees < Decimal("2")
    assert decision.qty == 0
    assert any("R:R after fees" in reason for reason in decision.reasons)


def test_kill_switch_at_exactly_ninety_percent():
    blocked = evaluate(_plan(), _account(equity=Decimal("18"), starting_equity=Decimal("20")))
    assert not blocked.allowed
    assert any(reason.startswith("kill switch") for reason in blocked.reasons)
    assert blocked.qty == 0

    open_ = evaluate(_plan(), _account(equity=Decimal("18.01"), starting_equity=Decimal("20")))
    assert open_.allowed


def test_second_position_is_blocked():
    decision = evaluate(_plan(), _account(open_positions=1))
    assert not decision.allowed
    assert any(reason.startswith("max 1") for reason in decision.reasons)


def test_short_and_perp_are_blocked():
    short = evaluate(_plan(side="Sell"), _account())
    assert not short.allowed
    assert any("long-only" in reason for reason in short.reasons)

    perp = evaluate(_plan(category="linear"), _account())
    assert not perp.allowed
    assert any("spot only" in reason for reason in perp.reasons)


def test_requested_qty_over_one_percent_is_rejected():
    decision = evaluate(_plan(), _account(), requested_qty=Decimal("10"))
    assert not decision.allowed
    assert any("1%" in reason for reason in decision.reasons)


def test_tight_stop_is_cash_capped_below_one_percent_risk():
    decision = evaluate(
        _plan(entry=Decimal("100"), stop=Decimal("99.9"), target=Decimal("102")),
        _account(),
    )
    assert decision.allowed
    assert decision.cash_limited
    assert decision.risk_fraction < Decimal("0.01")


def test_fee_rate_below_vip0_is_rejected():
    decision = evaluate(_plan(), _account(fee_rate=Decimal("0")))
    assert not decision.allowed
    assert any("VIP0" in reason for reason in decision.reasons)


def test_config_refuses_looser_rules():
    with pytest.raises(ConfigError):
        load_config({"DESK_MAX_RISK": "0.02"})
    with pytest.raises(ConfigError):
        load_config({"DESK_KILL_RATIO": "0.50"})
    with pytest.raises(ConfigError):
        load_config({"DESK_MIN_RR": "1.5"})
    with pytest.raises(ConfigError):
        load_config({"DESK_FEE_RATE": "0.0005"})
    with pytest.raises(ConfigError):
        load_config({"DESK_CATEGORY": "linear"})

    tighter = load_config({"DESK_MAX_RISK": "0.005", "DESK_MIN_RR": "3", "DESK_KILL_RATIO": "0.95"})
    assert tighter.max_risk == Decimal("0.005")
    assert tighter.min_rr == Decimal("3")
    assert tighter.kill_ratio == Decimal("0.95")
    assert tighter.api_key_set is False
    assert "secret" not in repr(tighter).lower() or "api_secret_set=False" in repr(tighter)
