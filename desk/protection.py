"""Paper protection for an open long. No exchange order.

On a blocking-event day (CPI, payroll, PCE, GDP, FOMC) the default check
acts only in [T−25min, T]. `madrugada=True` (the 06:05 America/Sao_Paulo
run) acts from 00:00 BRT until T. Under +1.00R the long is closed. At
+1.00R or better the stop is raised to entry×1.003 and never lowered.
If that breakeven would sit at or above the bid, or the 15m candles cannot
be read, the long is closed instead (`stop_nao_elevavel`).

A quote older than 120 seconds, or no quote, is retried 3 times. If it is
still not fresh, the position is flagged `pendente_zerar_pre_evento` and
not closed. Any later run closes that flag at a fresh bid with reason
`execucao_atrasada`, recording when it should have flattened, when it did,
the delay, and both prices.

Raising a stop first walks candles with the old stop, stamps
`ultimo_check_utc`, then appends the change. CPI on 14 Oct 2026 at 09:30 BRT
stays on the calendar through `desk.events`.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import ROUND_HALF_UP, Decimal

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
PRICE_RETRY_ATTEMPTS = 3
PRICE_RETRY_WAIT_S = 60
PRE_EVENT_WINDOW_MIN = 25
_R_FLOOR = Decimal("1")
QuoteFetch = Callable[[], "Quote | None"]
Sleep = Callable[[float], None]


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


def in_pre_event_window(
    now: datetime,
    event_at: datetime,
    *,
    madrugada: bool = False,
    minutes: int = PRE_EVENT_WINDOW_MIN,
) -> tuple[bool, str]:
    """[T−25min, T] by default. Madrugada is [00:00 BRT, T], the 06:05 run."""
    local_now = sao_paulo_now(now)
    local_event = sao_paulo_now(event_at)
    if madrugada:
        start = local_event.replace(hour=0, minute=0, second=0, microsecond=0)
        mode = "madrugada 00:00→T"
    else:
        start = local_event - timedelta(minutes=minutes)
        mode = f"T−{minutes}min→T"
    if local_now < start:
        return False, f"antes da janela {mode} (início {start.strftime('%H:%M:%S BRT')})"
    if local_now > local_event:
        return False, f"após o horário do evento ({local_event.strftime('%H:%M:%S BRT')})"
    return True, mode


def protect_before_event(
    ledger: Ledger,
    now: datetime,
    events: tuple[MacroEvent, ...] = (),
    *,
    quote: Quote | None = None,
    fetch_quote: QuoteFetch | None = None,
    candles_15m: list[Candle] | None = None,
    klines_failed: bool = False,
    writer: bool | None = None,
    madrugada: bool = False,
    sleep: Sleep | None = None,
    attempts: int = PRICE_RETRY_ATTEMPTS,
    wait_s: float = PRICE_RETRY_WAIT_S,
) -> ProtectionResult:
    """Paper pre-event check. A pending flatten flag runs before the window."""
    if ledger.position is not None and ledger.position.pendente_zerar_pre_evento:
        return _close_pending(
            ledger,
            now,
            quote=quote,
            fetch_quote=fetch_quote,
            writer=writer,
            sleep=sleep,
            attempts=attempts,
            wait_s=wait_s,
        )
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
    inside, detail = in_pre_event_window(now, event.at, madrugada=madrugada)
    if not inside:
        label = "madrugada 00:00→T" if madrugada else f"{PRE_EVENT_WINDOW_MIN} min pré-evento"
        return ProtectionResult(
            "noop",
            f"DECISÃO: noop — fora da janela {label} ({detail}).",
            applied=False,
        )
    fresh, log, err, last = _read_fresh_quote(
        now,
        quote=quote,
        fetch_quote=fetch_quote,
        sleep=sleep,
        attempts=attempts,
        wait_s=wait_s,
    )
    mode = "madrugada" if madrugada else f"T−{PRE_EVENT_WINDOW_MIN}min"
    header = f"[protecao-pre-evento] janela OK ({mode}) até {sao_paulo_now(event.at).strftime('%H:%M BRT')}\n{log}\n"
    if fresh is None:
        return _flag_pending(ledger, now, event.name, last, err or "indisponível", header, writer=writer, attempts=attempts)
    return _decide(
        ledger,
        now,
        event.name,
        fresh,
        candles_15m if candles_15m is not None else [],
        klines_failed=klines_failed,
        writer=writer,
        header=header,
    )


def _read_fresh_quote(
    now: datetime,
    *,
    quote: Quote | None,
    fetch_quote: QuoteFetch | None,
    sleep: Sleep | None,
    attempts: int,
    wait_s: float,
) -> tuple[Quote | None, str, str | None, Quote | None]:
    """Up to `attempts` reads. Returns (fresh, log, error, last quote seen)."""
    pause = sleep if sleep is not None else (lambda _seconds: None)
    lines: list[str] = []
    last: Quote | None = None
    last_err = "indisponível"
    for i in range(1, attempts + 1):
        try:
            got = fetch_quote() if fetch_quote is not None else quote
        except Exception as exc:
            got = None
            last = None
            last_err = f"indisponível ({exc})"
            lines.append(f"[preco] tentativa {i}/{attempts}: ERROR {last_err}")
        else:
            if got is None:
                last = None
                last_err = "indisponível"
                lines.append(f"[preco] tentativa {i}/{attempts}: ERROR {last_err}")
            else:
                last = got
                line = quote_line(got.collected_at, now)
                age = max(0.0, (_utc(now) - _utc(got.collected_at)).total_seconds())
                lines.append(f"[preco] tentativa {i}/{attempts}: {line}")
                if age <= PRICE_MAX_AGE.total_seconds():
                    return got, "\n".join(lines), None, got
                last_err = f"velho ({age:.0f}s > {int(PRICE_MAX_AGE.total_seconds())}s)"
        if i < attempts:
            lines.append(f"[preco] aguardando {wait_s:.0f}s para nova tentativa…")
            pause(wait_s)
    return None, "\n".join(lines), last_err, last


def _flag_pending(
    ledger: Ledger,
    now: datetime,
    event_name: str,
    last: Quote | None,
    err: str,
    header: str,
    *,
    writer: bool | None,
    attempts: int,
) -> ProtectionResult:
    ref = None if last is None else format(last.bid, "f")
    flag = {"evento": event_name, "desde_utc": _utc(now).isoformat(), "preco_ref": ref}
    message = (
        f"{header}ERROR: preço Bybit sem fresco após {attempts} tentativas ({err}). "
        f"Flag pendente_zerar_pre_evento gravada (evento={event_name!r}, desde={flag['desde_utc']}, "
        f"preco_ref={ref}). Nenhuma saída neste run."
    )
    if not ledger_writes_enabled(writer):
        return ProtectionResult("error", "RECUSADO: " + message, applied=False)
    assert ledger.position is not None
    ledger.position.pendente_zerar_pre_evento = flag
    return ProtectionResult("error", message, applied=False)


def _decide(
    ledger: Ledger,
    now: datetime,
    event_name: str,
    quote: Quote,
    candles_15m: list[Candle],
    *,
    klines_failed: bool,
    writer: bool | None,
    header: str,
) -> ProtectionResult:
    position = ledger.position
    assert position is not None
    line = quote_line(quote.collected_at, now)
    multiple = net_r_multiple(position.entry, _risk_stop(position), quote.bid)
    if multiple >= _R_FLOOR:
        target = breakeven_stop(position.entry)
        if target <= position.stop:
            return ProtectionResult(
                "noop",
                header + f"DECISÃO: noop-protegido — PnL≥+1R e stop já ≥ breakeven. {line}",
                applied=False,
                r_multiple=multiple,
            )
        if target >= quote.bid:
            note = (
                f"stop alvo {target} ≥ bid {quote.bid} — não elevável; fallback close."
            )
            return _close_pre(ledger, now, quote, event_name, "stop_nao_elevavel", header + note + "\n", writer, multiple)
        if klines_failed:
            note = "klines 15m falhou — fallback close."
            return _close_pre(ledger, now, quote, event_name, "stop_nao_elevavel", header + note + "\n", writer, multiple)
        raised = raise_stop_to_breakeven(
            ledger,
            quote.bid,
            now,
            candles_15m,
            reason="breakeven_+1R_pre_evento",
            writer=writer,
        )
        if raised.kind == "stop":
            return ProtectionResult(
                raised.kind,
                header + raised.message,
                applied=raised.applied,
                r_multiple=multiple,
                trade=raised.trade,
            )
        if raised.applied and ledger.position is not None:
            ledger.position.pendente_zerar_pre_evento = None
        return ProtectionResult(
            "raise_stop",
            header + f"DECISÃO: raise-stop — {raised.new_stop} por evento '{event_name}'. {line}",
            applied=raised.applied,
            r_multiple=multiple,
            new_stop=raised.new_stop,
        )
    return _close_pre(ledger, now, quote, event_name, "", header, writer, multiple)


def _close_pre(
    ledger: Ledger,
    now: datetime,
    quote: Quote,
    event_name: str,
    extra: str,
    header: str,
    writer: bool | None,
    multiple: Decimal,
) -> ProtectionResult:
    reason = f"pre-{event_name}" + (f" {extra}" if extra else "")
    line = quote_line(quote.collected_at, now)
    message = header + f"DECISÃO: close — motivo={reason!r} @ bid {quote.bid}. {line}"
    if not ledger_writes_enabled(writer):
        return ProtectionResult(
            "close",
            "RECUSADO: " + message,
            applied=False,
            r_multiple=multiple,
        )
    assert ledger.position is not None
    ledger.position.pendente_zerar_pre_evento = None
    closed = close_long(
        ledger,
        quote.bid,
        now,
        writer=True,
        reason=reason,
        bid_at_detection=quote.bid,
    )
    return ProtectionResult("close", message, applied=True, r_multiple=multiple, trade=closed.trade)


def _close_pending(
    ledger: Ledger,
    now: datetime,
    *,
    quote: Quote | None,
    fetch_quote: QuoteFetch | None,
    writer: bool | None,
    sleep: Sleep | None,
    attempts: int,
    wait_s: float,
) -> ProtectionResult:
    position = ledger.position
    assert position is not None
    flag = position.pendente_zerar_pre_evento or {}
    event_name = str(flag.get("evento") or "evento")
    fresh, log, err, _last = _read_fresh_quote(
        now,
        quote=quote,
        fetch_quote=fetch_quote,
        sleep=sleep,
        attempts=attempts,
        wait_s=wait_s,
    )
    header = (
        f"[pendente_zerar] flag desde={flag.get('desde_utc')} evento={event_name!r} "
        f"preco_ref={flag.get('preco_ref')}\n{log}\n"
    )
    if fresh is None:
        return ProtectionResult(
            "error",
            header + f"ERROR: pendente_zerar ainda sem preço fresco ({err}). Flag permanece; nenhuma saída.",
            applied=False,
        )
    fields = _delayed_fields(flag, fresh.bid, now)
    reason = f"pre-{event_name} execucao_atrasada"
    dif = fields["diferenca_pct"]
    dif_text = "n/a" if dif is None else format(dif, "f")
    message = (
        header
        + f"DECISÃO: close — {reason} @ bid fresco {fresh.bid} "
        + f"(atraso {fields['atraso_execucao_min']} min; "
        + f"ref={fields['preco_ref_quando_devia'] or 'null'} → exec={fresh.bid}; dif={dif_text}%). "
        + quote_line(fresh.collected_at, now)
    )
    if not ledger_writes_enabled(writer):
        return ProtectionResult("close", "RECUSADO: " + message, applied=False)
    closed = close_long(
        ledger,
        fresh.bid,
        now,
        writer=True,
        reason=reason,
        bid_at_detection=fresh.bid,
        devia_zerar_utc=fields["devia_zerar_utc"],
        executado_utc=fields["executado_utc"],
        atraso_execucao_min=fields["atraso_execucao_min"],
        preco_ref_quando_devia=fields["preco_ref_quando_devia"],
        preco_execucao=fields["preco_execucao"],
        diferenca_pct=fields["diferenca_pct"],
    )
    return ProtectionResult("close", message, applied=True, trade=closed.trade)


def _delayed_fields(flag: dict, preco_exec: Decimal, now: datetime) -> dict:
    raw = flag.get("desde_utc")
    try:
        desde = datetime.fromisoformat(str(raw))
        if desde.tzinfo is None:
            desde = desde.replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        desde = _utc(now)
    minutes = Decimal(str(max(0.0, (_utc(now) - _utc(desde)).total_seconds() / 60.0)))
    atraso = minutes.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)
    ref_raw = flag.get("preco_ref")
    ref = None if ref_raw in (None, "") else Decimal(str(ref_raw))
    dif = None
    if ref is not None and ref != 0:
        dif = ((preco_exec / ref) - 1) * Decimal("100")
        dif = dif.quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)
    return {
        "devia_zerar_utc": str(raw) if raw else _utc(desde).isoformat(),
        "executado_utc": _utc(now).isoformat(),
        "atraso_execucao_min": atraso,
        "preco_ref_quando_devia": ref,
        "preco_execucao": preco_exec,
        "diferenca_pct": dif,
    }


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
