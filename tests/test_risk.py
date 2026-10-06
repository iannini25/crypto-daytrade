"""Risk gate: cost bands, net R:R, one position, kill switch, loss lock."""

from datetime import datetime, timezone
from decimal import Decimal

import pytest

from desk.config import ConfigError, load_config
from desk.events import MacroEvent
from desk.risk import AccountSnapshot, OrderPlan, evaluate


def _plan(**overrides) -> OrderPlan:
    # 3.5% stop, 7.9% target: net R:R = (7.9 - 0.30) / (3.5 + 0.30) = 2.
    fields = dict(
        symbol="BTCUSDT",
        entry=Decimal("100"),
        stop=Decimal("96.5"),
        target=Decimal("107.9"),
    )
    fields.update(overrides)
    return OrderPlan(**fields)


def _account(**overrides) -> AccountSnapshot:
    fields = dict(equity=Decimal("19.9"), starting_equity=Decimal("19.9"), open_positions=0)
    fields.update(overrides)
    return AccountSnapshot(**fields)


def test_stop_one_percent_is_rejected_by_the_cost_rule():
    decision = evaluate(_plan(stop=Decimal("99"), target=Decimal("110")), _account())
    assert not decision.allowed
    assert decision.stop_band == "cost_reject"
    assert decision.qty == 0
    assert any("cost rule" in reason for reason in decision.reasons)
    assert decision.min_stop_percent == Decimal("3.0")


def test_stop_3_5_percent_with_target_7_9_percent_is_accepted():
    decision = evaluate(_plan(), _account())
    assert decision.allowed
    assert decision.stop_percent == Decimal("3.5")
    assert decision.target_percent == Decimal("7.9")
    assert decision.rr_after_fees == Decimal("2")
    assert decision.stop_band == "exception"
    assert "justification" in decision.band_label
    assert decision.qty > 0
    assert decision.notional >= Decimal("6")
    assert decision.risk_fraction <= Decimal("0.03")
    assert "1% zone" in decision.summary or "exception" in decision.summary


def test_stop_11_7_percent_is_rejected_by_the_account_cap():
    decision = evaluate(_plan(stop=Decimal("88.3"), target=Decimal("130")), _account())
    assert not decision.allowed
    assert decision.stop_band == "account_cap"
    assert decision.qty == 0
    assert any("account cap" in reason for reason in decision.reasons)
    assert decision.cap_stop_percent < Decimal("11.7")


def test_three_percent_stop_sits_in_the_one_percent_zone():
    decision = evaluate(_plan(stop=Decimal("97"), target=Decimal("106.9")), _account())
    assert decision.allowed
    assert decision.stop_band == "target_1pct"
    assert decision.risk_fraction <= Decimal("0.01")
    assert decision.risk_fraction > Decimal("0.009")


def test_kill_switch_at_exactly_ninety_percent():
    blocked = evaluate(_plan(), _account(equity=Decimal("18"), starting_equity=Decimal("20")))
    assert not blocked.allowed
    assert any(reason.startswith("kill switch") for reason in blocked.reasons)
    assert blocked.qty == 0

    open_ = evaluate(_plan(), _account(equity=Decimal("18.01"), starting_equity=Decimal("20")))
    assert open_.allowed


def test_second_position_and_a_loss_today_are_blocked():
    second = evaluate(_plan(), _account(open_positions=1))
    assert not second.allowed
    assert any(reason.startswith("max 1") for reason in second.reasons)

    lost = evaluate(_plan(), _account(losses_today=1))
    assert not lost.allowed
    assert any(reason.startswith("loss lock") for reason in lost.reasons)


def test_short_perp_and_15m_stop_are_blocked():
    short = evaluate(_plan(side="Sell"), _account())
    assert not short.allowed
    assert any("long-only" in reason for reason in short.reasons)

    perp = evaluate(_plan(category="linear"), _account())
    assert not perp.allowed
    assert any("spot only" in reason for reason in perp.reasons)

    micro = evaluate(_plan(stop_anchor="15m"), _account())
    assert not micro.allowed
    assert any("15m" in reason for reason in micro.reasons)


def test_atr_ceiling_rejects_a_wider_structure_stop():
    decision = evaluate(_plan(atr_ceiling=Decimal("1")), _account())
    assert not decision.allowed
    assert any("3xATR" in reason for reason in decision.reasons)


def test_session_and_event_locks_block_new_entries():
    outside = evaluate(
        _plan(),
        _account(),
        now=datetime(2026, 10, 6, 2, 0, tzinfo=timezone.utc),
    )
    assert not outside.allowed
    assert any(reason.startswith("outside 10:00") for reason in outside.reasons)

    friday_uom = evaluate(
        _plan(),
        _account(),
        now=datetime(2026, 10, 9, 14, 0, tzinfo=timezone.utc),
    )
    assert not friday_uom.allowed
    assert any("UoM" in reason for reason in friday_uom.reasons)

    cpi = MacroEvent(name="CPI", at=datetime(2026, 10, 13, 12, 30, tzinfo=timezone.utc))
    locked = evaluate(
        _plan(),
        _account(),
        now=datetime(2026, 10, 13, 12, 20, tzinfo=timezone.utc),
        events=(cpi,),
    )
    assert not locked.allowed
    assert any("CPI" in reason for reason in locked.reasons)


def test_requested_qty_over_the_cap_is_rejected():
    decision = evaluate(_plan(), _account(), requested_qty=Decimal("1"))
    assert not decision.allowed
    assert any("3%" in reason for reason in decision.reasons)


def test_fee_rate_below_vip0_is_rejected():
    decision = evaluate(_plan(), _account(fee_rate=Decimal("0")))
    assert not decision.allowed
    assert any("VIP0" in reason for reason in decision.reasons)


def test_stop_9_66_percent_is_an_exception_and_9_67_is_rejected():
    # 9.66% stop, 20.22% target: (20.22 - 0.30) / (9.66 + 0.30) = 2.
    accepted = evaluate(_plan(stop=Decimal("90.34"), target=Decimal("120.22")), _account())
    assert accepted.allowed
    assert accepted.stop_band == "exception"
    assert accepted.cap_stop_percent == Decimal("9.66")
    assert accepted.rr_after_fees == Decimal("2")

    rejected = evaluate(_plan(stop=Decimal("90.33"), target=Decimal("140")), _account())
    assert not rejected.allowed
    assert rejected.stop_band == "account_cap"
    assert rejected.qty == 0


def test_target_under_6_9_percent_is_rejected():
    decision = evaluate(_plan(stop=Decimal("97"), target=Decimal("106.8")), _account())
    assert not decision.allowed
    assert any("6.9%" in reason for reason in decision.reasons)
    floor = evaluate(_plan(stop=Decimal("97"), target=Decimal("106.9")), _account())
    assert floor.allowed
    assert floor.target_percent == Decimal("6.9")
    assert floor.stop_band == "target_1pct"


def test_three_trades_today_block_a_new_entry():
    blocked = evaluate(_plan(), _account(trades_today=3))
    assert not blocked.allowed
    assert blocked.qty == 0
    assert any(reason.startswith("trade cap") for reason in blocked.reasons)
    open_ = evaluate(_plan(), _account(trades_today=2))
    assert open_.allowed


def test_exit_only_pattern_never_opens_a_short_or_a_long():
    decision = evaluate(_plan(pattern="double_top", side="Buy"), _account())
    assert not decision.allowed
    assert decision.qty == 0
    assert any("never open a short" in reason for reason in decision.reasons)
    assert decision.summary.find("Sell") == -1

    bear = evaluate(_plan(pattern="descending_triangle", pattern_timeframe="1h"), _account())
    assert not bear.allowed
    assert any("exit-only" in reason for reason in bear.reasons)


def test_mid_pattern_stop_and_15m_reversal_are_rejected():
    # A 3% stop above the structural low (96.5) would otherwise clear the cost gate.
    mid = evaluate(
        _plan(stop=Decimal("97"), target=Decimal("106.9"), pattern_low=Decimal("96.5")),
        _account(),
    )
    assert not mid.allowed
    assert any("mid-pattern" in reason for reason in mid.reasons)

    reversal = evaluate(
        _plan(pattern="double_bottom", pattern_timeframe="15m"),
        _account(),
    )
    assert not reversal.allowed
    assert any("not an active long" in reason for reason in reversal.reasons)

    daily = evaluate(
        _plan(pattern="double_bottom", pattern_timeframe="D", pattern_low=Decimal("96.5")),
        _account(),
    )
    assert daily.allowed

    cup = evaluate(_plan(pattern="cup", pattern_timeframe="D"), _account())
    assert not cup.allowed
    assert any("outside playbook" in reason for reason in cup.reasons)


def test_config_refuses_looser_rules():
    with pytest.raises(ConfigError):
        load_config({"DESK_MAX_RISK": "0.02"})
    with pytest.raises(ConfigError):
        load_config({"DESK_RISK_CAP": "0.05"})
    with pytest.raises(ConfigError):
        load_config({"DESK_MIN_ORDER_USDT": "1"})
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
    assert tighter.risk_cap == Decimal("0.03")
    assert tighter.api_key_set is False
    assert "api_secret_set=False" in repr(tighter)
