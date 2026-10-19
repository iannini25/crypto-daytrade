"""Bearish-figure exit on a closed 1h candle. Paper only.

The first closed 1h bar with close < figura_min is an exit. On that same
bar the stop is checked first: if the low trades through the stop then in
force, the stop wins. The fill the caller records is min(close_1h, live bid).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from desk.bybit import Candle
from desk.stops import StopChange, stop_in_force

FIGURE_EXIT = "saida_por_figura"


@dataclass(frozen=True)
class FigureEvent:
    kind: str  # "stop" or "figura"
    fill: Decimal
    candle_open: datetime
    when: datetime
    reason: str
    stop_used: Decimal | None = None
    close_1h: Decimal | None = None
    figura_min: Decimal | None = None


def _parse(value: datetime | str) -> datetime:
    if isinstance(value, datetime):
        moment = value
    else:
        moment = datetime.fromisoformat(value)
    if moment.tzinfo is None:
        raise ValueError("figure timestamps must be timezone-aware")
    return moment.astimezone(timezone.utc)


def walk_figure(
    candles: list[Candle],
    *,
    stop: Decimal,
    history: tuple[StopChange, ...] | list[StopChange],
    figura_min: Decimal | None,
    armed_at: datetime | str | None,
    ultimo_check: datetime | str | None,
    now: datetime,
) -> FigureEvent | None:
    """Walk closed 1h bars after the arm (or the last check, if later)."""
    if figura_min is None or not armed_at:
        return None
    since = _parse(armed_at)
    if ultimo_check:
        checked = _parse(ultimo_check)
        if checked > since:
            since = checked
    end = _parse(now)
    hour = timedelta(hours=1)
    ordered = sorted(candles, key=lambda candle: candle.start_ms)
    for candle in ordered:
        opened = datetime.fromtimestamp(candle.start_ms / 1000, tz=timezone.utc)
        closed = opened + hour
        if not (closed > since and closed <= end):
            continue
        vigente = stop_in_force(stop, history, opened)
        if candle.low <= vigente:
            fill = candle.open if candle.open <= vigente else vigente
            return FigureEvent(
                kind="stop",
                fill=fill,
                candle_open=opened,
                when=opened,
                reason=f"stop atingido em {vigente}",
                stop_used=vigente,
            )
        if candle.close < figura_min:
            return FigureEvent(
                kind="figura",
                fill=candle.close,
                candle_open=opened,
                when=closed,
                reason=FIGURE_EXIT,
                close_1h=candle.close,
                figura_min=figura_min,
            )
    return None


def figure_fill(close_1h: Decimal, bid: Decimal) -> Decimal:
    """Worse price for the long: the lower of the 1h close and the live bid."""
    return close_1h if close_1h <= bid else bid


@dataclass(frozen=True)
class FigureExit:
    event: FigureEvent
    applied: bool
    fill: Decimal
    trade: object | None = None


def exit_on_figure(ledger, candles: list[Candle], now: datetime, bid: Decimal, *, writer: bool | None = None):
    """Close the paper long on the first figure or stop hit. No exchange call.

    A figure fill is min(close_1h, bid). Both prices are stored on the trade.
    On the same 1h candle the stop wins. Dry-run unless the writer flag is on.
    Cash uses the desk fee model: the fill is not cut by a second slippage debit.
    """
    from desk.paper import close_long

    position = ledger.position
    if position is None or position.figura_min is None or not position.figura_armed_at_utc:
        return None
    event = walk_figure(
        candles,
        stop=position.stop,
        history=position.stop_hist,
        figura_min=position.figura_min,
        armed_at=position.figura_armed_at_utc,
        ultimo_check=position.ultimo_check_utc,
        now=now,
    )
    if event is None:
        return None
    if event.kind == "stop":
        reason = f"{event.reason}; stop_usado={event.stop_used}"
        closed = close_long(
            ledger,
            event.fill,
            event.when,
            writer=writer,
            reason=reason,
            stop_used=event.stop_used,
        )
        fill = event.fill
    else:
        assert event.close_1h is not None
        fill = figure_fill(event.close_1h, bid)
        closed = close_long(
            ledger,
            fill,
            event.when,
            writer=writer,
            reason=FIGURE_EXIT,
            close_1h=event.close_1h,
            bid_at_detection=bid,
        )
    return FigureExit(event=event, applied=closed.applied, fill=fill, trade=closed.trade)
