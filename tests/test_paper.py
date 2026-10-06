"""Simulated ledger stays local and respects the gate."""

from datetime import datetime, timezone
from decimal import Decimal

import pytest

from desk.fees import round_trip_pnl
from desk.paper import PaperError, close_long, default_ledger, open_long, save_ledger
from desk.risk import OrderPlan


def _plan() -> OrderPlan:
    return OrderPlan(
        symbol="ETHUSDT",
        entry=Decimal("100"),
        stop=Decimal("98"),
        target=Decimal("110"),
    )


def test_open_and_flat_close_match_fee_formula(tmp_path):
    ledger = default_ledger(Decimal("20"))
    when = datetime(2026, 10, 6, 13, 30, tzinfo=timezone.utc)
    decision = open_long(ledger, _plan(), now=when)
    assert decision.allowed
    assert ledger.position is not None
    debit = decision.qty * Decimal("100") * Decimal("1.001")
    assert ledger.cash == Decimal("20") - debit

    with pytest.raises(PaperError):
        open_long(ledger, _plan(), now=when)

    trade = close_long(ledger, Decimal("100"), now=when)
    assert trade.pnl == round_trip_pnl(Decimal("100"), Decimal("100"), decision.qty)
    assert ledger.position is None
    assert ledger.cash == Decimal("20") + trade.pnl

    path = tmp_path / "ledger.json"
    save_ledger(ledger, path)
    text = path.read_text(encoding="utf-8")
    assert "ETHUSDT" in text
    assert "api" not in text.lower()


def test_kill_switch_blocks_a_new_paper_long():
    ledger = default_ledger(Decimal("20"))
    ledger.cash = Decimal("18")
    with pytest.raises(PaperError, match="kill switch"):
        open_long(ledger, _plan())
    assert ledger.position is None
    assert ledger.cash == Decimal("18")
