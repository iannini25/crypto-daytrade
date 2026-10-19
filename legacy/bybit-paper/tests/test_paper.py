"""Simulated ledger stays local, read-only by default, and respects the gate."""

from datetime import datetime, timezone
from decimal import Decimal

import pytest

from desk.events import MacroEvent
from desk.fees import round_trip_pnl
from desk.paper import (
    PaperError,
    close_long,
    default_ledger,
    ledger_writes_enabled,
    manage_into_event,
    open_long,
    save_ledger,
    stop_fill_price,
)
from desk.risk import OrderPlan

WHEN = datetime(2026, 10, 6, 13, 30, tzinfo=timezone.utc)


def _plan() -> OrderPlan:
    return OrderPlan(
        symbol="ETHUSDT",
        entry=Decimal("100"),
        stop=Decimal("96.5"),
        target=Decimal("107.9"),
    )


def test_stop_is_live_outside_the_window_and_a_gap_fills_at_the_open():
    assert stop_fill_price(Decimal("96.5"), Decimal("100"), Decimal("97")) is None
    assert stop_fill_price(Decimal("96.5"), Decimal("100"), Decimal("96.5")) == Decimal("96.5")
    assert stop_fill_price(Decimal("96.5"), Decimal("96"), Decimal("95")) == Decimal("96")


def test_open_and_flat_close_match_fee_formula(tmp_path, monkeypatch):
    monkeypatch.delenv("LEDGER_WRITER", raising=False)
    ledger = default_ledger(Decimal("19.9"))
    preview = open_long(ledger, _plan(), now=WHEN)
    assert preview.dry_run and not preview.applied
    assert ledger.position is None
    assert ledger.cash == Decimal("19.9")

    decision = open_long(ledger, _plan(), now=WHEN, writer=True)
    assert decision.applied
    assert decision.decision is not None and decision.decision.allowed
    assert ledger.position is not None
    qty = decision.decision.qty
    debit = qty * Decimal("100") * Decimal("1.001")
    assert ledger.cash == Decimal("19.9") - debit

    with pytest.raises(PaperError):
        open_long(ledger, _plan(), now=WHEN, writer=True)

    closed = close_long(ledger, Decimal("100"), now=WHEN, writer=True)
    assert closed.trade is not None
    assert closed.trade.pnl == round_trip_pnl(Decimal("100"), Decimal("100"), qty)
    assert ledger.position is None
    assert ledger.cash == Decimal("19.9") + closed.trade.pnl

    path = tmp_path / "ledger.json"
    with pytest.raises(PaperError, match="read-only"):
        save_ledger(ledger, path)
    assert not path.exists()
    assert ledger_writes_enabled() is False
    save_ledger(ledger, path, writer=True)
    text = path.read_text(encoding="utf-8")
    assert "ETHUSDT" in text
    assert "api" not in text.lower()


def test_a_loss_blocks_the_rest_of_the_sao_paulo_day():
    ledger = default_ledger(Decimal("19.9"))
    open_long(ledger, _plan(), now=WHEN, writer=True)
    close_long(ledger, Decimal("100"), now=WHEN, writer=True)
    with pytest.raises(PaperError, match="loss lock"):
        open_long(ledger, _plan(), now=WHEN, writer=True)
    assert ledger.position is None


def test_kill_switch_blocks_a_new_paper_long():
    ledger = default_ledger(Decimal("20"))
    ledger.cash = Decimal("18")
    with pytest.raises(PaperError, match="kill switch"):
        open_long(ledger, _plan(), writer=True)
    assert ledger.position is None
    assert ledger.cash == Decimal("18")


def test_event_management_is_dry_run_until_the_writer_flag(monkeypatch):
    monkeypatch.delenv("LEDGER_WRITER", raising=False)
    ledger = default_ledger(Decimal("19.9"))
    open_long(ledger, _plan(), now=WHEN, writer=True)
    cpi = MacroEvent(name="CPI", at=datetime(2026, 10, 13, 12, 30, tzinfo=timezone.utc))
    before = datetime(2026, 10, 13, 12, 20, tzinfo=timezone.utc)
    # Mark is only +1% and the stop is 3.5%, so this is under +1R.
    preview = manage_into_event(ledger, Decimal("101"), before, (cpi,))
    assert preview.dry_run
    assert preview.event is not None and preview.event.kind == "close"
    assert ledger.position is not None

    # A mark at +1R (gain% = stop% + 0.60 = 4.1) raises the stop instead.
    winner = manage_into_event(ledger, Decimal("104.1"), before, (cpi,), writer=True)
    assert winner.applied
    assert winner.event is not None and winner.event.kind == "raise_stop"
    assert ledger.position is not None
    assert ledger.position.stop == Decimal("100") * Decimal("1.003")
