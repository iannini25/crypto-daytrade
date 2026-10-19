"""Stop in force at a candle's open. Paper only.

Before a stop is raised, walk candles with the old stop up to now, stamp
`ultimo_check_utc`, then append `{old, new, at_utc, reason}`. A later walk
uses the stop that was vigente at each candle's open, so the new stop is
not applied backwards. A gap through the stop fills at min(open, stop).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from desk.bybit import Candle


@dataclass(frozen=True)
class StopChange:
    old: Decimal
    new: Decimal
    at_utc: datetime
    reason: str

    def to_json(self) -> dict[str, str]:
        return {
            "old": format(self.old, "f"),
            "new": format(self.new, "f"),
            "at_utc": _iso(self.at_utc),
            "reason": self.reason,
        }

    @classmethod
    def from_json(cls, payload: dict) -> StopChange:
        return cls(
            old=Decimal(str(payload["old"])),
            new=Decimal(str(payload["new"])),
            at_utc=_parse(str(payload["at_utc"])),
            reason=str(payload.get("reason", "")),
        )


@dataclass(frozen=True)
class StopHit:
    fill: Decimal
    stop_used: Decimal
    candle_open: datetime


def _parse(value: datetime | str) -> datetime:
    if isinstance(value, datetime):
        moment = value
    else:
        moment = datetime.fromisoformat(value)
    if moment.tzinfo is None:
        raise ValueError("stop timestamps must be timezone-aware")
    return moment.astimezone(timezone.utc)


def _iso(moment: datetime) -> str:
    return _parse(moment).isoformat()


def stop_in_force(stop: Decimal, history: tuple[StopChange, ...] | list[StopChange], when: datetime) -> Decimal:
    """Stop that applied at `when` (the candle open).

    Before the first change the stop is that change's `old`. At and after
    each `at_utc` it is that change's `new`. With no history, `stop` itself.
    """
    if not history:
        return stop
    moment = _parse(when)
    if moment < _parse(history[0].at_utc):
        return history[0].old
    vigente = history[0].old
    for change in history:
        if moment >= _parse(change.at_utc):
            vigente = change.new
        else:
            break
    return vigente


def append_stop_change(
    history: list[StopChange],
    old: Decimal,
    new: Decimal,
    at_utc: datetime,
    reason: str,
) -> StopChange:
    change = StopChange(old=old, new=new, at_utc=_parse(at_utc), reason=reason)
    history.append(change)
    return change


def walk_stop(
    candles: list[Candle],
    *,
    stop: Decimal,
    history: tuple[StopChange, ...] | list[StopChange],
    since: datetime,
    now: datetime,
    bar_minutes: int,
) -> StopHit | None:
    """First closed candle whose low trades through the stop then in force.

    A candle counts when its close time is after `since` and at or before
    `now`. The fill is min(open, stop). The stop used is the one vigente at
    the candle open.
    """
    start = _parse(since)
    end = _parse(now)
    duration = timedelta(minutes=bar_minutes)
    ordered = sorted(candles, key=lambda candle: candle.start_ms)
    for candle in ordered:
        opened = datetime.fromtimestamp(candle.start_ms / 1000, tz=timezone.utc)
        closed = opened + duration
        if not (closed > start and closed <= end):
            continue
        vigente = stop_in_force(stop, history, opened)
        if candle.low <= vigente:
            fill = candle.open if candle.open <= vigente else vigente
            return StopHit(fill=fill, stop_used=vigente, candle_open=opened)
    return None
