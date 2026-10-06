"""Event locks. Paper management only. Nothing here places an order.

New entries are blocked:

- from 15 minutes before until 15 minutes after CPI, FOMC, payroll, or PCE
- on Fridays 10:45–11:15 America/Sao_Paulo (University of Michigan window)

Fifteen minutes before a lock, an open long is handled on the paper ledger
only when LEDGER_WRITER=1:

- unrealized net R under +1: close
- unrealized net R at least +1: move the stop to entry plus the 0.30% cost and hold
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, time, timedelta
from decimal import Decimal
from pathlib import Path

from desk.fees import COST_PERCENT, ROUND_TRIP_COST
from desk.session import sao_paulo_now

MACRO_NAMES = frozenset({"CPI", "FOMC", "payroll", "PCE"})
LOCK_PAD = timedelta(minutes=15)
UOM_START = time(10, 45)
UOM_END = time(11, 15)


@dataclass(frozen=True)
class MacroEvent:
    name: str
    at: datetime

    def __post_init__(self) -> None:
        if self.name not in MACRO_NAMES:
            raise ValueError(f"event must be one of {sorted(MACRO_NAMES)}")
        if self.at.tzinfo is None:
            raise ValueError("event time must be timezone-aware")


@dataclass(frozen=True)
class EventAction:
    """What the paper book should do. `kind` is none, close, or raise_stop."""

    kind: str
    reason: str
    new_stop: Decimal | None = None
    r_multiple: Decimal | None = None


def load_events(path: str | Path | None) -> tuple[MacroEvent, ...]:
    if not path:
        return ()
    file_path = Path(path)
    if not file_path.is_file():
        return ()
    raw = json.loads(file_path.read_text(encoding="utf-8"))
    events: list[MacroEvent] = []
    for item in raw:
        moment = datetime.fromisoformat(str(item["at"]))
        if moment.tzinfo is None:
            raise ValueError("event timestamps need a timezone offset")
        events.append(MacroEvent(name=str(item["name"]), at=moment))
    return tuple(events)


def friday_uom_lock(now: datetime) -> bool:
    """Inclusive Friday 10:45–11:15 America/Sao_Paulo."""
    local = sao_paulo_now(now)
    if local.weekday() != 4:
        return False
    current = local.time().replace(microsecond=0)
    return UOM_START <= current <= UOM_END


def _active_macro(now: datetime, events: tuple[MacroEvent, ...]) -> MacroEvent | None:
    for event in events:
        if event.at - LOCK_PAD <= now <= event.at + LOCK_PAD:
            return event
    return None


def entry_lock(now: datetime, events: tuple[MacroEvent, ...] = ()) -> str | None:
    """Reason string when a new entry is blocked, else None."""
    if friday_uom_lock(now):
        return "event lock: Friday UoM 10:45-11:15 America/Sao_Paulo"
    event = _active_macro(now, events)
    if event is not None:
        return f"event lock: no new entries within 15 minutes of {event.name}"
    return None


def net_r_multiple(entry: Decimal, stop: Decimal, mark: Decimal, cost_percent: Decimal = COST_PERCENT) -> Decimal:
    """Unrealized R with the same 0.30 cost the entry gate uses.

    The initial stop is -1R. +1R means the open gain, after cost, matches the
    stop distance after cost.
    """
    if entry <= 0 or stop >= entry:
        raise ValueError("need a long stop below entry")
    gain_pct = (mark - entry) / entry * Decimal("100")
    stop_pct = (entry - stop) / entry * Decimal("100")
    return (gain_pct - cost_percent) / (stop_pct + cost_percent)


def entry_plus_costs(entry: Decimal, cost_fraction: Decimal = ROUND_TRIP_COST) -> Decimal:
    """Stop that scratches after the round-trip cost. Above entry for a long."""
    return entry * (Decimal("1") + cost_fraction)


def pre_event_action(
    *,
    entry: Decimal,
    stop: Decimal,
    mark: Decimal,
    now: datetime,
    events: tuple[MacroEvent, ...] = (),
) -> EventAction:
    """Recommend a paper action inside the 15 minutes before a lock, and during it.

    Outside that window the kind is `none` (overnight holds are allowed).
    """
    trigger = _management_window(now, events)
    if trigger is None:
        return EventAction("none", "no lock inside the management window")
    multiple = net_r_multiple(entry, stop, mark)
    if multiple < Decimal("1"):
        return EventAction(
            "close",
            f"under +1R before {trigger}; close on the paper book 15 minutes before the lock",
            r_multiple=multiple,
        )
    raised = entry_plus_costs(entry)
    new_stop = stop if stop >= raised else raised
    return EventAction(
        "raise_stop",
        f"at least +1R before {trigger}; move stop to entry+costs and hold",
        new_stop=new_stop,
        r_multiple=multiple,
    )


def _management_window(now: datetime, events: tuple[MacroEvent, ...]) -> str | None:
    """Name of a lock whose pre-event action is due (from T-15 through the lock)."""
    local = sao_paulo_now(now)
    if local.weekday() == 4:
        start = local.replace(hour=10, minute=45, second=0, microsecond=0)
        begin = start - LOCK_PAD
        end = local.replace(hour=11, minute=15, second=0, microsecond=0)
        if begin <= local <= end:
            return "Friday UoM"
    for event in events:
        if event.at - LOCK_PAD <= now <= event.at + LOCK_PAD:
            return event.name
    return None


def hold_horizon(opened_at: datetime, now: datetime) -> str:
    """Overnight is allowed. The swing horizon is 1 to 5 days."""
    if opened_at.tzinfo is None or now.tzinfo is None:
        raise ValueError("timestamps must be timezone-aware")
    days = (now - opened_at).total_seconds() / 86400
    if days > 5:
        return "past_5_days"
    return "within_1_to_5_days"
