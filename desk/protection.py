"""Paper protection for an open long. No exchange order.

On a blocking-event day (CPI, payroll, PCE, GDP, FOMC) the scheduled checks
are 06:05 America/Sao_Paulo and then every 30 minutes from 09:10 (09:10,
09:40, ...). Under +1.00R the long is closed. At +1.00R or better the stop
is raised to entry×1.003 and never lowered. A quote older than 120 seconds,
or no quote, is an error and writes nothing.

Raising a stop first walks candles with the old stop, stamps
`ultimo_check_utc`, then appends the change. CPI on 14 Oct 2026 at 09:30 BRT
stays on the calendar through `desk.events`.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from desk.bybit import Candle
from desk.events import BLOCKING_EVENTS, MacroEvent, net_r_multiple, with_builtin_events
from desk.paper import (
    ClosedTrade,
    Ledger,
    PaperError,
    close_long,
    ledger_writes_enabled,
)
from desk.session import sao_paulo_now
from desk.stops import StopHit, walk_stop

BREAKEVEN_MULT = Decimal("1.003")
PRICE_MAX_AGE = timedelta(seconds=120)
_R_FLOOR = Decimal("1")


@dataclass(frozen=True)
class Quote:
    bid: Decimal
    last: Decimal
    collected_at: datetime


@dataclass(frozen=True)
class ProtectionResult:
    kind: str
    message: str
    applied: bool
    r_multiple: Decimal | None = None
    trade: ClosedTrade | None = None
    new_stop: Decimal | None = None


def is_protection_slot(now: datetime) -> bool:
    """True at 06:05 BRT and every 30 minutes from 09:10 BRT."""
    local = sao_paulo_now(now)
    if local.second != 0 or local.microsecond != 0:
        return False
    minutes = local.hour * 60 + local.minute
    if minutes == 6 * 60 + 5:
        return True
    first = 9 * 60 + 10
    return minutes >= first and (minutes - first) % 30 == 0


def quote_line(collected_at: datetime, now: datetime) -> str:
    """BRT collection time and age in seconds. Printed on every protection run."""
    age = max(0.0, (_utc(now) - _utc(collected_at)).total_seconds())
    local = sao_paulo_now(collected_at)
    stamp = local.strftime("%Y-%m-%d %H:%M:%S BRT")
    return f"preço Bybit coletado {stamp} (idade {age:.0f}s)"


def blocking_event_today(now: datetime, events: tuple[MacroEvent, ...] = ()) -> MacroEvent | None:
    local_day = sao_paulo_now(now).date()
    found: MacroEvent | None = None
    for event in with_builtin_events(events):
        if event.name not in BLOCKING_EVENTS:
            continue
        if sao_paulo_now(event.at).date() == local_day:
            found = event
    return found


def breakeven_stop(entry: Decimal) -> Decimal:
    return entry * BREAKEVEN_MULT


def raise_stop_to_breakeven(
    ledger: Ledger,
    mark_bid: Decimal,
    now: datetime,
    candles_15m: list[Candle],
    *,
    reason: str,
    writer: bool | None = None,
) -> ProtectionResult:
    """Raise to entry×1.003 only at >= +1.00R. 0.99R is refused. Never lowers.

    The old stop is walked up to `now` first. A hit closes the paper long and
    does not raise. Otherwise `ultimo_check_utc` is stamped, then the change
    is appended.
    """
    if ledger.position is None:
        return ProtectionResult("none", "nenhuma posição aberta", applied=False)
    position = ledger.position
    target = breakeven_stop(position.entry)
    if target <= position.stop:
        return ProtectionResult(
            "unchanged",
            f"stop já está em {position.stop} ≥ breakeven {target} — não desce",
            applied=False,
        )
    multiple = net_r_multiple(position.entry, _risk_stop(position), mark_bid)
    if multiple < _R_FLOOR:
        return ProtectionResult(
            "refused",
            f"NÃO move stop: PnL marcado {multiple}R < +1R",
            applied=False,
            r_multiple=multiple,
        )
    since = _since(position)
    hit = walk_stop(
        candles_15m,
        stop=position.stop,
        history=position.stop_hist,
        since=since,
        now=now,
        bar_minutes=15,
    )
    if hit is not None:
        return _close_on_stop(ledger, hit, now, writer=writer, multiple=multiple)
    if not ledger_writes_enabled(writer):
        return ProtectionResult(
            "raise_stop",
            f"RECUSADO: dry-run {position.stop} → {target} ({reason})",
            applied=False,
            r_multiple=multiple,
            new_stop=target,
        )
    position.ultimo_check_utc = _utc(now).isoformat()
    position.record_stop(position.stop, target, now, reason)
    return ProtectionResult(
        "raise_stop",
        f"STOP → BREAKEVEN {target} ({reason})",
        applied=True,
        r_multiple=multiple,
        new_stop=target,
    )


def protect_before_event(
    ledger: Ledger,
    now: datetime,
    events: tuple[MacroEvent, ...] = (),
    *,
    quote: Quote | None,
    candles_15m: list[Candle] | None = None,
    writer: bool | None = None,
) -> ProtectionResult:
    """Event-day protection. Error on a stale or missing quote writes nothing."""
    event = blocking_event_today(now, events)
    if event is None:
        day = sao_paulo_now(now).date().isoformat()
        return ProtectionResult("noop", f"DECISÃO: noop — sem evento de bloqueio em {day}.", applied=False)
    if ledger.position is None:
        return ProtectionResult(
            "noop",
            f"DECISÃO: noop — evento '{event.name}' mas nenhuma posição aberta.",
            applied=False,
        )
    if quote is None:
        return ProtectionResult(
            "error",
            "ERROR: preço Bybit indisponível. Nenhuma escrita.",
            applied=False,
        )
    line = quote_line(quote.collected_at, now)
    age = _utc(now) - _utc(quote.collected_at)
    if age > PRICE_MAX_AGE:
        return ProtectionResult(
            "error",
            f"ERROR: preço Bybit velho ({int(age.total_seconds())}s > 120s). {line}. Nenhuma escrita.",
            applied=False,
        )
    position = ledger.position
    multiple = net_r_multiple(position.entry, _risk_stop(position), quote.bid)
    header = f"{line}\n"
    if multiple >= _R_FLOOR:
        raised = raise_stop_to_breakeven(
            ledger,
            quote.bid,
            now,
            candles_15m or [],
            reason="breakeven_+1R_pre_evento",
            writer=writer,
        )
        if raised.kind == "unchanged":
            return ProtectionResult(
                "noop",
                header + f"DECISÃO: noop-protegido — PnL≥+1R e stop já ≥ breakeven. {line}",
                applied=False,
                r_multiple=multiple,
            )
        if raised.kind == "stop":
            return ProtectionResult(
                raised.kind,
                header + raised.message,
                applied=raised.applied,
                r_multiple=multiple,
                trade=raised.trade,
            )
        return ProtectionResult(
            "raise_stop",
            header + f"DECISÃO: raise-stop — {raised.new_stop} por evento '{event.name}'. {line}",
            applied=raised.applied,
            r_multiple=multiple,
            new_stop=raised.new_stop,
        )
    reason = f"pre-{event.name}"
    if not ledger_writes_enabled(writer):
        return ProtectionResult(
            "close",
            header + f"RECUSADO: DECISÃO: close — PnL {multiple}R < +1R; motivo={reason!r}. {line}",
            applied=False,
            r_multiple=multiple,
        )
    closed = close_long(
        ledger,
        quote.bid,
        now,
        writer=True,
        reason=reason,
        bid_at_detection=quote.bid,
    )
    return ProtectionResult(
        "close",
        header + f"DECISÃO: close — PnL {multiple}R < +1R; motivo={reason!r}. {line}",
        applied=True,
        r_multiple=multiple,
        trade=closed.trade,
    )


def _close_on_stop(
    ledger: Ledger,
    hit: StopHit,
    now: datetime,
    *,
    writer: bool | None,
    multiple: Decimal,
) -> ProtectionResult:
    message = f"stop atingido em {hit.stop_used}; stop_usado={hit.stop_used}"
    if not ledger_writes_enabled(writer):
        return ProtectionResult("stop", message, applied=False, r_multiple=multiple)
    closed = close_long(
        ledger,
        hit.fill,
        hit.candle_open,
        writer=True,
        reason=message,
        stop_used=hit.stop_used,
    )
    return ProtectionResult("stop", message, applied=True, r_multiple=multiple, trade=closed.trade)


def _risk_stop(position) -> Decimal:
    """+1R is measured on the stop the trade was opened with."""
    initial = position.stop_initial if position.stop_initial is not None else position.stop
    if initial >= position.entry:
        raise PaperError("risk stop must sit below entry")
    return initial


def _since(position) -> datetime:
    raw = position.ultimo_check_utc or position.opened_at
    moment = datetime.fromisoformat(raw)
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return moment


def _utc(moment: datetime) -> datetime:
    if moment.tzinfo is None:
        raise PaperError("timestamps must be timezone-aware")
    return moment.astimezone(timezone.utc)
