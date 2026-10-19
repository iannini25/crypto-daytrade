"""Breakeven only at +1.00R, and the event-day protection schedule."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from desk.events import entry_lock
from desk.fees import COST_PERCENT
from desk.paper import Ledger, default_ledger, open_long
from desk.protection import (
    Quote,
    in_pre_event_window,
    is_protection_slot,
    protect_before_event,
    raise_stop_to_breakeven,
)
from desk.risk import OrderPlan

UTC = timezone.utc
WHEN = datetime(2026, 10, 6, 13, 30, tzinfo=UTC)
CPI_MORNING = datetime(2026, 10, 14, 9, 5, tzinfo=UTC)  # 06:05 BRT, madrugada slot
IN_WINDOW = datetime(2026, 10, 14, 12, 10, tzinfo=UTC)  # 09:10 BRT, inside [T−25, T]


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
    quote = _quote(_mark("0.99"), IN_WINDOW)
    closed = protect_before_event(ledger, IN_WINDOW, quote=quote, writer=True)
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
        IN_WINDOW,
        quote=_quote(_mark("1.00"), IN_WINDOW, age_s=3),
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


def test_stale_quote_retries_then_flags_without_closing(monkeypatch):
    ledger = _book(monkeypatch)
    assert ledger.position is not None
    before = ledger.position.stop
    bid = _mark("1.20")
    slept: list[float] = []
    stale = protect_before_event(
        ledger,
        IN_WINDOW,
        quote=_quote(bid, IN_WINDOW, age_s=180),
        writer=True,
        sleep=slept.append,
    )
    assert stale.kind == "error"
    assert stale.applied is False
    assert "ERROR" in stale.message
    assert "velho" in stale.message
    assert "pendente_zerar_pre_evento" in stale.message
    assert "preço Bybit coletado" in stale.message
    assert "idade" in stale.message
    assert slept == [60, 60]
    assert ledger.position is not None
    assert ledger.position.stop == before
    assert ledger.position.stop_hist == []
    assert ledger.trades == []
    flag = ledger.position.pendente_zerar_pre_evento
    assert flag is not None
    assert flag["preco_ref"] == format(bid, "f")
    assert flag["evento"] == "CPI"

    missing_book = _book(monkeypatch)
    missing = protect_before_event(missing_book, IN_WINDOW, quote=None, writer=True, sleep=lambda _s: None)
    assert missing.kind == "error"
    assert "indisponível" in missing.message
    assert missing.applied is False
    assert missing_book.position is not None
    assert missing_book.position.stop == before
    assert missing_book.position.pendente_zerar_pre_evento is not None
    assert missing_book.position.pendente_zerar_pre_evento["preco_ref"] is None
    assert missing_book.trades == []


def test_protection_without_the_writer_does_not_close(monkeypatch):
    ledger = _book(monkeypatch)
    result = protect_before_event(
        ledger,
        IN_WINDOW,
        quote=_quote(_mark("0.50"), IN_WINDOW),
        writer=False,
    )
    assert result.applied is False
    assert "RECUSADO" in result.message
    assert ledger.position is not None
    assert ledger.position.pendente_zerar_pre_evento is None


def test_default_window_is_t_minus_25_through_t(monkeypatch):
    event_at = datetime(2026, 10, 14, 12, 30, tzinfo=UTC)
    start = event_at - timedelta(minutes=25)
    assert in_pre_event_window(start, event_at)[0] is True
    assert in_pre_event_window(start - timedelta(seconds=1), event_at)[0] is False
    assert in_pre_event_window(event_at, event_at)[0] is True
    assert in_pre_event_window(event_at + timedelta(minutes=1), event_at)[0] is False

    ledger = _book(monkeypatch)
    closed = protect_before_event(
        ledger,
        start,
        quote=_quote(_mark("0.50"), start),
        writer=True,
        sleep=lambda _s: None,
    )
    assert "fora da janela" not in closed.message
    assert "DECISÃO: close" in closed.message
    assert ledger.position is None

    early = _book(monkeypatch)
    assert early.position is not None
    before = early.position.stop
    skipped = protect_before_event(
        early,
        start - timedelta(seconds=1),
        quote=_quote(_mark("0.50"), start),
        writer=True,
    )
    assert skipped.kind == "noop"
    assert "fora da janela" in skipped.message
    assert early.position.stop == before
    assert early.position.pendente_zerar_pre_evento is None

    at_print = _book(monkeypatch)
    acted = protect_before_event(
        at_print,
        event_at,
        quote=_quote(_mark("0.50"), event_at),
        writer=True,
        sleep=lambda _s: None,
    )
    assert "DECISÃO: close" in acted.message

    late = _book(monkeypatch)
    after = protect_before_event(
        late,
        event_at + timedelta(minutes=1),
        quote=_quote(_mark("0.50"), event_at),
        writer=True,
    )
    assert after.kind == "noop"
    assert "fora da janela" in after.message
    assert late.position is not None


def test_madrugada_covers_0605_and_the_default_window_does_not(monkeypatch):
    ledger = _book(monkeypatch)
    closed = protect_before_event(
        ledger,
        CPI_MORNING,
        quote=_quote(_mark("0.50"), CPI_MORNING),
        writer=True,
        madrugada=True,
        sleep=lambda _s: None,
    )
    assert "madrugada" in closed.message
    assert "DECISÃO: close" in closed.message
    assert closed.trade is not None
    assert closed.trade.reason.startswith("pre-CPI")
    assert ledger.position is None

    plain = _book(monkeypatch)
    assert plain.position is not None
    before = plain.position.stop
    skipped = protect_before_event(
        plain,
        CPI_MORNING,
        quote=_quote(_mark("0.50"), CPI_MORNING),
        writer=True,
    )
    assert skipped.kind == "noop"
    assert "fora da janela" in skipped.message
    assert plain.position.stop == before

    quiet = _book(monkeypatch)
    assert quiet.position is not None
    stop = quiet.position.stop
    no_event = protect_before_event(
        quiet,
        WHEN,
        quote=_quote(Decimal("100"), WHEN),
        writer=True,
        madrugada=True,
    )
    assert no_event.kind == "noop"
    assert "sem evento" in no_event.message
    assert quiet.position.stop == stop

    after_print = _book(monkeypatch)
    late = datetime(2026, 10, 14, 12, 31, tzinfo=UTC)
    past = protect_before_event(
        after_print,
        late,
        quote=_quote(_mark("0.50"), late),
        writer=True,
        madrugada=True,
    )
    assert past.kind == "noop"
    assert "fora da janela" in past.message
    assert after_print.position is not None


def test_second_fresh_attempt_decides_and_does_not_flag(monkeypatch):
    ledger = _book(monkeypatch)
    bid = _mark("0.40")
    calls = {"n": 0}

    def fetch() -> Quote:
        calls["n"] += 1
        age = 200 if calls["n"] == 1 else 5
        return _quote(bid, IN_WINDOW, age_s=age)

    slept: list[float] = []
    result = protect_before_event(
        ledger,
        IN_WINDOW,
        fetch_quote=fetch,
        writer=True,
        sleep=slept.append,
    )
    assert "tentativa 2/" in result.message
    assert "DECISÃO: close" in result.message
    assert slept == [60]
    assert ledger.position is None


def test_pending_flag_closes_later_at_a_fresh_price(monkeypatch):
    ledger = _book(monkeypatch)
    assert ledger.position is not None
    desde = datetime(2026, 10, 6, 9, 5, tzinfo=UTC)
    executed = datetime(2026, 10, 6, 12, 10, tzinfo=UTC)
    ledger.position.pendente_zerar_pre_evento = {
        "evento": "CPI",
        "desde_utc": desde.isoformat(),
        "preco_ref": "100",
    }
    result = protect_before_event(
        ledger,
        executed,
        quote=_quote(Decimal("98"), executed, age_s=2),
        writer=True,
        sleep=lambda _s: None,
    )
    assert result.applied
    assert "execucao_atrasada" in result.message
    assert ledger.position is None
    assert result.trade is not None
    assert result.trade.reason == "pre-CPI execucao_atrasada"
    assert result.trade.exit_price == Decimal("98")
    assert result.trade.preco_execucao == Decimal("98")
    assert result.trade.preco_ref_quando_devia == Decimal("100")
    assert result.trade.diferenca_pct == Decimal("-2.000")
    assert result.trade.atraso_execucao_min == Decimal("185.0")
    assert result.trade.devia_zerar_utc == desde.isoformat()
    assert result.trade.executado_utc == executed.isoformat()
    again = type(result.trade).from_json(result.trade.to_json())
    assert again.diferenca_pct == Decimal("-2.000")
    assert again.atraso_execucao_min == Decimal("185.0")

    still = _book(monkeypatch)
    assert still.position is not None
    still.position.pendente_zerar_pre_evento = {
        "evento": "CPI",
        "desde_utc": desde.isoformat(),
        "preco_ref": "100",
    }
    held = protect_before_event(
        still,
        CPI_MORNING,
        quote=_quote(Decimal("98"), CPI_MORNING, age_s=180),
        writer=True,
        sleep=lambda _s: None,
    )
    assert held.kind == "error"
    assert "Flag permanece" in held.message
    assert still.position is not None
    assert still.position.pendente_zerar_pre_evento is not None


def test_unplaceable_breakeven_or_failed_klines_closes(monkeypatch):
    ledger = _book(monkeypatch)
    monkeypatch.setattr("desk.protection.net_r_multiple", lambda *args, **kwargs: Decimal("1.2"))
    bid = Decimal("100.2")
    closed = protect_before_event(
        ledger,
        IN_WINDOW,
        quote=_quote(bid, IN_WINDOW),
        writer=True,
        sleep=lambda _s: None,
    )
    assert "stop_nao_elevavel" in closed.message
    assert "fallback close" in closed.message
    assert "DECISÃO: close" in closed.message
    assert ledger.position is None
    assert closed.trade is not None
    assert "stop_nao_elevavel" in closed.trade.reason

    book = _book(monkeypatch)
    failed = protect_before_event(
        book,
        IN_WINDOW,
        quote=_quote(_mark("1.00"), IN_WINDOW),
        writer=True,
        klines_failed=True,
        sleep=lambda _s: None,
    )
    assert "fallback close" in failed.message
    assert "stop_nao_elevavel" in failed.message
    assert book.position is None
    assert failed.trade is not None
    assert "stop_nao_elevavel" in failed.trade.reason
