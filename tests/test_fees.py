"""Fee math. VIP0 is 0.10% per side, 0.20% round trip."""

from decimal import Decimal

from desk.fees import (
    ROUND_TRIP_FEE,
    VIP0_SIDE_FEE,
    breakeven_win_rate,
    expectancy,
    gross_rr,
    net_gain_per_unit,
    net_loss_per_unit,
    net_rr,
    round_trip_pnl,
)


def test_headline_round_trip_is_twenty_bps():
    assert VIP0_SIDE_FEE == Decimal("0.001")
    assert ROUND_TRIP_FEE == Decimal("0.002")
    assert VIP0_SIDE_FEE + VIP0_SIDE_FEE == ROUND_TRIP_FEE


def test_flat_round_trip_loses_exactly_twenty_bps():
    pnl = round_trip_pnl(Decimal("100"), Decimal("100"), Decimal("1"))
    assert pnl == Decimal("-0.2")
    notional = Decimal("100")
    assert pnl / notional == -ROUND_TRIP_FEE


def test_gross_two_r_fails_after_fees():
    entry, stop, target = Decimal("100"), Decimal("99"), Decimal("102")
    assert gross_rr(entry, stop, target) == Decimal("2")
    assert net_loss_per_unit(entry, stop) == Decimal("1.199")
    assert net_gain_per_unit(entry, target) == Decimal("1.798")
    assert net_rr(entry, stop, target) < Decimal("2")


def test_wider_target_clears_two_r_after_fees():
    entry, stop, target = Decimal("100"), Decimal("98"), Decimal("110")
    assert net_loss_per_unit(entry, stop) == Decimal("2.198")
    assert net_gain_per_unit(entry, target) == Decimal("9.79")
    assert net_rr(entry, stop, target) > Decimal("2")


def test_expectancy_breaks_even_at_one_third_for_two_r():
    rate = breakeven_win_rate(Decimal("2"))
    assert rate == Decimal("1") / Decimal("3")
    # 1/3 is a repeating decimal; the residual is far below a cent on a $20 book.
    assert abs(expectancy(Decimal("2"), Decimal("1"), rate)) < Decimal("1e-20")
    assert expectancy(Decimal("2"), Decimal("1"), Decimal("0.5")) == Decimal("0.5")
