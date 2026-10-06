"""Stop in force at each candle, and a raise does not apply backwards."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from desk.bybit import Candle
from desk.paper import close_long, default_ledger, open_long
from desk.protection import raise_stop_to_breakeven
from desk.risk import OrderPlan
from desk.stops import StopChange, stop_in_force, walk_stop

UTC = timezone.utc
WHEN = datetime(2026, 10, 6, 13, 30, tzinfo=UTC)


def _plan() -> OrderPlan:
    return OrderPlan(
        symbol="BTCUSDT",
        entry=Decimal("100"),
        stop=Decimal("96.5"),
        target=Decimal("107.9"),
    )


def _candle(open_at: datetime, o, h, l, c) -> Candle:
    return Candle(
        start_ms=int(open_at.timestamp() * 1000),
        open=Decimal(str(o)),
        high=Decimal(str(h)),
        low=Decimal(str(l)),
        close=Decimal(str(c)),
        volume=Decimal("1"),
        turnover=Decimal("1"),
    )


def _hist() -> list[StopChange]:
    return [
        StopChange(
            old=Decimal("93"),
            new=Decimal("100.3"),
            at_utc=datetime(2026, 10, 6, 9, 10, tzinfo=UTC),
            reason="breakeven_+1R",
        )
    ]


def test_stop_in_force_without_history_is_the_live_stop():
    assert stop_in_force(Decimal("90"), [], datetime(2026, 10, 6, 12, tzinfo=UTC)) == Decimal("90")


def test_stop_in_force_uses_old_before_the_raise_and_new_after():
    hist = _hist()
    assert stop_in_force(Decimal("100.3"), hist, datetime(2026, 10, 6, 8, tzinfo=UTC)) == Decimal("93")
    assert stop_in_force(Decimal("100.3"), hist, datetime(2026, 10, 6, 9, 10, tzinfo=UTC)) == Decimal("100.3")
    assert stop_in_force(Decimal("100.3"), hist, datetime(2026, 10, 6, 14, tzinfo=UTC)) == Decimal("100.3")


def test_lows_that_only_touch_the_new_level_before_the_raise_do_not_fire():
    hist = _hist()
    start = datetime(2026, 10, 6, 6, tzinfo=UTC)
    candles = [_candle(start + timedelta(minutes=15 * i), 101, 102, 100, 101) for i in range(13)]
    now = datetime(2026, 10, 6, 14, 5, tzinfo=UTC)
    assert walk_stop(candles, stop=Decimal("100.3"), history=hist, since=datetime(2026, 10, 6, 5, tzinfo=UTC), now=now, bar_minutes=15) is None
    assert walk_stop(candles, stop=Decimal("100.3"), history=hist, since=datetime(2026, 10, 6, 9, 10, tzinfo=UTC), now=now, bar_minutes=15) is None


def test_after_the_raise_the_new_level_fires_and_records_the_stop_used():
    hit = walk_stop(
        [_candle(datetime(2026, 10, 6, 10, tzinfo=UTC), 101, 102, 100, "100.5")],
        stop=Decimal("100.3"),
        history=_hist(),
        since=datetime(2026, 10, 6, 9, 10, tzinfo=UTC),
        now=datetime(2026, 10, 6, 14, 5, tzinfo=UTC),
        bar_minutes=15,
    )
    assert hit is not None
    assert hit.stop_used == Decimal("100.3")
    assert hit.fill == min(Decimal("101"), Decimal("100.3"))
    assert hit.fill == Decimal("100.3")


def test_a_gap_through_fills_at_the_open():
    hit = walk_stop(
        [_candle(datetime(2026, 10, 6, 9, tzinfo=UTC), 98, 99, 97, "98.5")],
        stop=Decimal("100"),
        history=[],
        since=datetime(2026, 10, 6, 8, tzinfo=UTC),
        now=datetime(2026, 10, 6, 14, tzinfo=UTC),
        bar_minutes=15,
    )
    assert hit is not None
    assert hit.fill == Decimal("98")
    assert hit.stop_used == Decimal("100")


def test_a_raise_walks_the_old_stop_first_and_stamps_before_appending(monkeypatch):
    monkeypatch.delenv("LEDGER_WRITER", raising=False)
    ledger = default_ledger(Decimal("19.9"))
    open_long(ledger, _plan(), now=WHEN, writer=True)
    assert ledger.position is not None
    now = datetime(2026, 10, 6, 14, tzinfo=UTC)
    pierced = _candle(WHEN, 100, 101, 96, 97)
    stopped = raise_stop_to_breakeven(
        ledger,
        Decimal("104.1"),
        now,
        [pierced],
        reason="breakeven_+1R",
        writer=True,
    )
    assert stopped.kind == "stop"
    assert stopped.applied
    assert ledger.position is None
    assert stopped.trade is not None
    assert stopped.trade.stop_used == Decimal("96.5")
    assert "stop_usado=96.5" in stopped.trade.reason
    assert stopped.trade.exit_price == Decimal("96.5")

    ledger = default_ledger(Decimal("19.9"))
    open_long(ledger, _plan(), now=WHEN, writer=True)
    quiet = _candle(WHEN, 100, 101, 97, 100)
    raised = raise_stop_to_breakeven(
        ledger,
        Decimal("104.1"),
        now,
        [quiet],
        reason="breakeven_+1R",
        writer=True,
    )
    assert raised.applied
    assert ledger.position is not None
    assert ledger.position.stop == Decimal("100") * Decimal("1.003")
    assert ledger.position.ultimo_check_utc == now.isoformat()
    assert len(ledger.position.stop_hist) == 1
    change = ledger.position.stop_hist[0]
    assert change.old == Decimal("96.5")
    assert change.new == ledger.position.stop
    assert change.at_utc == now
    assert change.reason == "breakeven_+1R"
    assert ledger.position.stop_initial == Decimal("96.5")


def test_closed_trade_keeps_stop_usado_through_json():
    ledger = default_ledger(Decimal("19.9"))
    open_long(ledger, _plan(), now=WHEN, writer=True)
    closed = close_long(
        ledger,
        Decimal("96"),
        now=WHEN,
        writer=True,
        reason="stop atingido; stop_usado=96.5",
        stop_used=Decimal("96.5"),
    )
    assert closed.trade is not None
    again = type(closed.trade).from_json(closed.trade.to_json())
    assert again.stop_used == Decimal("96.5")
    assert "stop_usado" in again.reason
