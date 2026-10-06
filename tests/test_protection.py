"""Breakeven only at +1.00R, and the event-day protection schedule."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from desk.events import entry_lock
from desk.fees import COST_PERCENT
from desk.paper import Ledger, default_ledger, open_long
from desk.protection import (
    Quote,
    is_protection_slot,
    protect_before_event,
    raise_stop_to_breakeven,
)
from desk.risk import OrderPlan

UTC = timezone.utc
WHEN = datetime(2026, 10, 6, 13, 30, tzinfo=UTC)
CPI_MORNING = datetime(2026, 10, 14, 9, 5, tzinfo=UTC)  # 06:05 BRT


def _plan() -> OrderPlan:
    return OrderPlan(
        symbol="BTCUSDT",
        entry=Decimal("100"),
        stop=Decimal("96.5"),
        target=Decimal("107.9"),
    )


def _mark(multiple: str) -> Decimal:
    entry = Decimal("100")
    stop = Decimal("96.5")
    stop_pct = (entry - stop) / entry * Decimal("100")
    gain_pct = Decimal(multiple) * (stop_pct + COST_PERCENT) + COST_PERCENT
    return entry * (Decimal("1") + gain_pct / Decimal("100"))


def _book(monkeypatch) -> Ledger:
    monkeypatch.delenv("LEDGER_WRITER", raising=False)
    ledger = default_ledger(Decimal("19.9"))
    open_long(ledger, _plan(), now=WHEN, writer=True)
    return ledger


def _quote(bid: Decimal, now: datetime, age_s: int = 5) -> Quote:
    return Quote(bid=bid, last=bid, collected_at=now - timedelta(seconds=age_s))


def test_breakeven_refuses_0_99r_and_accepts_1_00r(monkeypatch):
    ledger = _book(monkeypatch)
    now = datetime(2026, 10, 6, 14, tzinfo=UTC)
    refused = raise_stop_to_breakeven(
        ledger, _mark("0.99"), now, [], reason="breakeven_+1R", writer=True
    )
    assert refused.kind == "refused"
    assert "NÃO move stop" in refused.message
    assert ledger.position is not None
    assert ledger.position.stop == Decimal("96.5")
    assert ledger.position.stop_hist == []

    raised = raise_stop_to_breakeven(
        ledger, _mark("1.00"), now, [], reason="breakeven_+1R", writer=True
    )
    assert raised.applied
    assert "BREAKEVEN" in raised.message
    assert ledger.position.stop == Decimal("100") * Decimal("1.003")
    assert ledger.position.stop_hist[-1].reason == "breakeven_+1R"
    assert ledger.position.ultimo_check_utc == now.isoformat()


def test_breakeven_never_lowers_and_dry_run_writes_nothing(monkeypatch):
    ledger = _book(monkeypatch)
    assert ledger.position is not None
    ledger.position.stop = Decimal("100.5")
    now = datetime(2026, 10, 6, 14, tzinfo=UTC)
    held = raise_stop_to_breakeven(
        ledger, _mark("1.20"), now, [], reason="breakeven_+1R", writer=True
    )
    assert "não desce" in held.message
    assert ledger.position.stop == Decimal("100.5")
    assert ledger.position.stop_hist == []

    ledger.position.stop = Decimal("96.5")
    dry = raise_stop_to_breakeven(
        ledger, _mark("1.00"), now, [], reason="breakeven_+1R", writer=False
    )
    assert dry.applied is False
    assert "RECUSADO" in dry.message
    assert ledger.position.stop == Decimal("96.5")
    assert ledger.position.stop_hist == []


def test_protection_slots_and_cpi_14_oct_stays_on_the_calendar():
    assert is_protection_slot(datetime(2026, 10, 14, 9, 5, tzinfo=UTC))
    assert is_protection_slot(datetime(2026, 10, 14, 12, 10, tzinfo=UTC))
    assert is_protection_slot(datetime(2026, 10, 14, 12, 40, tzinfo=UTC))
    assert is_protection_slot(datetime(2026, 10, 14, 12, 11, tzinfo=UTC)) is False
    assert is_protection_slot(datetime(2026, 10, 14, 12, 10, 1, tzinfo=UTC)) is False
    assert "CPI" in entry_lock(datetime(2026, 10, 14, 12, 15, tzinfo=UTC), ())


def test_under_1r_on_cpi_day_closes_and_1r_raises(monkeypatch):
    ledger = _book(monkeypatch)
    quote = _quote(_mark("0.99"), CPI_MORNING)
    closed = protect_before_event(ledger, CPI_MORNING, quote=quote, writer=True)
    assert closed.applied
    assert closed.kind == "close"
    assert "DECISÃO: close" in closed.message
    assert "preço Bybit coletado" in closed.message
    assert "idade" in closed.message
    assert "BRT" in closed.message
    assert ledger.position is None
    assert closed.trade is not None
    assert closed.trade.reason.startswith("pre-CPI")

    ledger = _book(monkeypatch)
    raised = protect_before_event(
        ledger,
        CPI_MORNING,
        quote=_quote(_mark("1.00"), CPI_MORNING, age_s=3),
        writer=True,
    )
    assert raised.applied
    assert "raise-stop" in raised.message
    assert "idade" in raised.message
    assert "preço Bybit coletado" in raised.message
    assert ledger.position is not None
    assert ledger.position.stop == Decimal("100") * Decimal("1.003")
    assert ledger.position.stop_hist[-1].reason == "breakeven_+1R_pre_evento"


def test_no_event_and_no_position_are_noop(monkeypatch):
    ledger = _book(monkeypatch)
    assert ledger.position is not None
    before = ledger.position.stop
    quiet = protect_before_event(
        ledger,
        WHEN,
        quote=_quote(Decimal("104.1"), WHEN),
        writer=True,
    )
    assert quiet.kind == "noop"
    assert "noop" in quiet.message
    assert ledger.position.stop == before

    empty = default_ledger(Decimal("19.9"))
    flat = protect_before_event(empty, CPI_MORNING, quote=_quote(Decimal("100"), CPI_MORNING), writer=True)
    assert flat.kind == "noop"
    assert empty.position is None


def test_stale_or_missing_quote_is_an_error_and_writes_nothing(monkeypatch):
    ledger = _book(monkeypatch)
    assert ledger.position is not None
    before = ledger.position.stop
    stale = protect_before_event(
        ledger,
        CPI_MORNING,
        quote=_quote(_mark("1.20"), CPI_MORNING, age_s=180),
        writer=True,
    )
    assert stale.kind == "error"
    assert "ERROR" in stale.message
    assert "velho" in stale.message
    assert "preço Bybit coletado" in stale.message
    assert "idade" in stale.message
    assert stale.applied is False
    assert ledger.position is not None
    assert ledger.position.stop == before
    assert ledger.position.stop_hist == []

    missing = protect_before_event(ledger, CPI_MORNING, quote=None, writer=True)
    assert missing.kind == "error"
    assert "indisponível" in missing.message
    assert missing.applied is False
    assert ledger.position.stop == before


def test_protection_without_the_writer_does_not_close(monkeypatch):
    ledger = _book(monkeypatch)
    result = protect_before_event(
        ledger,
        CPI_MORNING,
        quote=_quote(_mark("0.50"), CPI_MORNING),
        writer=False,
    )
    assert result.applied is False
    assert "RECUSADO" in result.message
    assert ledger.position is not None
