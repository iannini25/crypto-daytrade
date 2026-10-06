"""Event locks. Paper management only. Nothing here places an order.

New entries are blocked:

- from 15 minutes before until 15 minutes after CPI, FOMC, payroll, PCE, or GDP
- on Fridays 10:45–11:15 America/Sao_Paulo (University of Michigan window)
- around the built-in CPI on 14 Oct 2026 at 09:30 America/Sao_Paulo

An open long on a blocking-event day (CPI, payroll, PCE, GDP, FOMC) is
handled by the scheduled paper check in `desk.protection`: 06:05
America/Sao_Paulo, then 09:10, 09:40, and every 30 minutes after that.
Under +1R the long is closed. At +1R or better the stop is raised to
entry×1.003 and never lowered. A quote older than 120 seconds, or no quote,
writes nothing.

`pre_event_action` still recommends the same close-or-raise inside the lock
window, so a missed scheduled check is not silent. It does not fire for the
whole event day. Ledger changes require LEDGER_WRITER=1.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, time, timedelta
from decimal import Decimal
from pathlib import Path

from desk.fees import COST_PERCENT, ROUND_TRIP_COST
from desk.session import SAO_PAULO, sao_paulo_now

MACRO_NAMES = frozenset({"CPI", "FOMC", "payroll", "PCE", "GDP"})
BLOCKING_EVENTS = frozenset({"CPI", "payroll", "PCE", "GDP", "FOMC"})
LOCK_PAD = timedelta(minutes=15)
UOM_START = time(10, 45)
UOM_END = time(11, 15)
# Checklist item 11. 14 Oct 2026, 09:30 America/Sao_Paulo (12:30 UTC).
CPI_2026_10_14 = datetime(2026, 10, 14, 9, 30, tzinfo=SAO_PAULO)


@dataclass(frozen=True)
class MacroEvent:
    name: str
    at: datetime

    def __post_init__(self) -> None:
        if self.name not in MACRO_NAMES:
            raise ValueError(f"event must be one of {sorted(MACRO_NAMES)}")
        if self.at.tzinfo is None:
            raise ValueError("event time must be timezone-aware")


BUILTIN_EVENTS = (MacroEvent(name="CPI", at=CPI_2026_10_14),)


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


def with_builtin_events(events: tuple[MacroEvent, ...] = ()) -> tuple[MacroEvent, ...]:
    """JSON events plus the playbook's CPI on 14 Oct 2026 at 09:30 BRT."""
    seen = {(event.name, event.at) for event in events}
    extra = tuple(event for event in BUILTIN_EVENTS if (event.name, event.at) not in seen)
    return events + extra


def entry_lock(now: datetime, events: tuple[MacroEvent, ...] = ()) -> str | None:
    """Reason string when a new entry is blocked, else None."""
    if friday_uom_lock(now):
        return "event lock: Friday UoM 10:45-11:15 America/Sao_Paulo"
    event = _active_macro(now, with_builtin_events(events))
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
    trigger = _management_window(now, with_builtin_events(events))
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
    """Overnight is allowed. The swing horizon is 1 to 5 days.

    The stop stays live for those days, including outside 10:00–12:30.
    A gap through the stop fills at the open (`desk.paper.stop_fill_price`).
    """
    if opened_at.tzinfo is None or now.tzinfo is None:
        raise ValueError("timestamps must be timezone-aware")
    days = (now - opened_at).total_seconds() / 86400
    if days > 5:
        return "past_5_days"
    return "within_1_to_5_days"
