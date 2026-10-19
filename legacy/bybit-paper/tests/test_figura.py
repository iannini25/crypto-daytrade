"""Figure exit on the first closed 1h candle. The stop wins on the same bar."""

from datetime import datetime, timezone
from decimal import Decimal

from desk.bybit import Candle
from desk.figura import FIGURE_EXIT, exit_on_figure, walk_figure
from desk.paper import default_ledger, open_long
from desk.risk import OrderPlan
from desk.stops import StopChange

UTC = timezone.utc
WHEN = datetime(2026, 10, 6, 13, 30, tzinfo=UTC)


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


def _walk(candles, *, stop="90", figura="99", armed="2026-10-06T14:30:00+00:00", now="2026-10-06T18:00:00+00:00", hist=()):
    return walk_figure(
        candles,
        stop=Decimal(stop),
        history=list(hist),
        figura_min=None if figura is None else Decimal(figura),
        armed_at=None if armed is None else armed,
        ultimo_check=armed,
        now=datetime.fromisoformat(now),
    )


def test_first_closed_1h_close_under_figura_min_exits_at_the_close_time():
    candles = [
        _candle(datetime(2026, 10, 6, 14, tzinfo=UTC), 100, 101, 99, "100.5"),
        _candle(datetime(2026, 10, 6, 15, tzinfo=UTC), "100.5", 101, "99.5", 100),
        _candle(datetime(2026, 10, 6, 16, tzinfo=UTC), 100, "100.5", 98, 97),
        _candle(datetime(2026, 10, 6, 17, tzinfo=UTC), 97, 98, 96, "97.5"),
    ]
    event = _walk(candles)
    assert event is not None
    assert event.kind == "figura"
    assert event.reason == FIGURE_EXIT
    assert event.close_1h == Decimal("97")
    assert event.when == datetime(2026, 10, 6, 17, tzinfo=UTC)


def test_stop_wins_when_the_same_1h_candle_hits_both():
    candles = [
        _candle(datetime(2026, 10, 6, 14, tzinfo=UTC), 100, 101, 99, "100.5"),
        _candle(datetime(2026, 10, 6, 15, tzinfo=UTC), "100.5", 101, "99.5", 100),
        _candle(datetime(2026, 10, 6, 16, tzinfo=UTC), 100, "100.5", 89, 97),
    ]
    event = _walk(candles, stop="90")
    assert event is not None
    assert event.kind == "stop"
    assert event.stop_used == Decimal("90")
    assert "stop atingido" in event.reason
    assert event.when == datetime(2026, 10, 6, 16, tzinfo=UTC)


def test_no_trigger_and_an_unarmed_figure_are_noop():
    quiet = [
        _candle(datetime(2026, 10, 6, 16, tzinfo=UTC), 100, 101, "99.5", 100),
    ]
    assert _walk(quiet, figura="95") is None
    assert _walk(quiet, figura=None, armed=None) is None


def test_an_unclosed_1h_candle_is_not_an_exit():
    candles = [
        _candle(datetime(2026, 10, 6, 14, tzinfo=UTC), 100, 101, 99, "100.5"),
        _candle(datetime(2026, 10, 6, 15, tzinfo=UTC), "100.5", 101, "99.5", 100),
        _candle(datetime(2026, 10, 6, 16, tzinfo=UTC), 100, "100.5", 98, "100.2"),
        _candle(datetime(2026, 10, 6, 17, tzinfo=UTC), "100.2", 101, 90, 90),
    ]
    assert _walk(candles, now="2026-10-06T17:30:00+00:00") is None


def test_after_a_raise_the_new_stop_wins_and_a_clean_close_is_the_figure():
    hist = [
        StopChange(
            old=Decimal("93"),
            new=Decimal("100.3"),
            at_utc=datetime(2026, 10, 6, 9, 10, tzinfo=UTC),
            reason="breakeven_+1R",
        )
    ]
    early = _candle(datetime(2026, 10, 6, 7, tzinfo=UTC), 101, 102, 100, "100.5")
    later = _candle(datetime(2026, 10, 6, 10, tzinfo=UTC), 101, 102, 100, "100.5")
    event = walk_figure(
        [early, later],
        stop=Decimal("100.3"),
        history=hist,
        figura_min=Decimal("99"),
        armed_at="2026-10-06T06:00:00+00:00",
        ultimo_check="2026-10-06T06:00:00+00:00",
        now=datetime(2026, 10, 6, 14, tzinfo=UTC),
    )
    assert event is not None and event.kind == "stop"
    assert event.stop_used == Decimal("100.3")
    assert event.when == datetime(2026, 10, 6, 10, tzinfo=UTC)

    consistent = _candle(datetime(2026, 10, 6, 10, tzinfo=UTC), 101, 102, 98, 98)
    event = walk_figure(
        [consistent],
        stop=Decimal("97"),
        history=[
            StopChange(
                old=Decimal("93"),
                new=Decimal("97"),
                at_utc=datetime(2026, 10, 6, 9, 10, tzinfo=UTC),
                reason="breakeven_+1R",
            )
        ],
        figura_min=Decimal("99"),
        armed_at="2026-10-06T06:00:00+00:00",
        ultimo_check="2026-10-06T06:00:00+00:00",
        now=datetime(2026, 10, 6, 14, tzinfo=UTC),
    )
    assert event is not None and event.kind == "figura"
    assert event.reason == FIGURE_EXIT


def test_figure_fill_is_min_of_close_and_bid_and_both_are_stored(monkeypatch):
    monkeypatch.delenv("LEDGER_WRITER", raising=False)
    ledger = default_ledger(Decimal("19.9"))
    open_long(
        ledger,
        OrderPlan(symbol="BTCUSDT", entry=Decimal("100"), stop=Decimal("96.5"), target=Decimal("107.9")),
        now=WHEN,
        writer=True,
    )
    assert ledger.position is not None
    ledger.position.figura_min = Decimal("99")
    ledger.position.figura_desc = "OCO 1h"
    ledger.position.figura_armed_at_utc = "2026-10-06T14:00:00+00:00"
    ledger.position.ultimo_check_utc = "2026-10-06T14:00:00+00:00"
    candle = _candle(datetime(2026, 10, 6, 15, tzinfo=UTC), 100, 101, "97.5", "98.5")
    bid = Decimal("97")
    result = exit_on_figure(
        ledger,
        [candle],
        datetime(2026, 10, 6, 17, tzinfo=UTC),
        bid,
        writer=True,
    )
    assert result is not None
    assert result.applied
    assert result.fill == Decimal("97")
    assert result.trade is not None
    assert result.trade.exit_price == Decimal("97")
    assert result.trade.close_1h == Decimal("98.5")
    assert result.trade.bid_at_detection == bid
    assert result.trade.reason == FIGURE_EXIT
    assert ledger.position is None


def test_same_candle_stop_records_stop_usado_on_the_trade(monkeypatch):
    monkeypatch.delenv("LEDGER_WRITER", raising=False)
    ledger = default_ledger(Decimal("19.9"))
    open_long(
        ledger,
        OrderPlan(symbol="ETHUSDT", entry=Decimal("100"), stop=Decimal("96.5"), target=Decimal("107.9")),
        now=WHEN,
        writer=True,
    )
    assert ledger.position is not None
    ledger.position.figura_min = Decimal("99")
    ledger.position.figura_armed_at_utc = "2026-10-06T14:00:00+00:00"
    candle = _candle(datetime(2026, 10, 6, 15, tzinfo=UTC), 100, 101, 96, 90)
    result = exit_on_figure(ledger, [candle], datetime(2026, 10, 6, 17, tzinfo=UTC), Decimal("95"), writer=True)
    assert result is not None
    assert result.event.kind == "stop"
    assert result.trade is not None
    assert result.trade.stop_used == Decimal("96.5")
    assert "stop_usado" in result.trade.reason
    assert result.trade.close_1h is None
