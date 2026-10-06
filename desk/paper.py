"""Simulated USDT ledger.

Fills exist only in a local JSON file. Nothing here talks to Bybit.
"""

from __future__ import annotations

import fcntl
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

from desk.events import EventAction, MacroEvent, pre_event_action
from desk.fees import VIP0_SIDE_FEE
from desk.risk import AccountSnapshot, GateDecision, OrderPlan, evaluate
from desk.session import sao_paulo_now

LEDGER_WRITER_ENV = "LEDGER_WRITER"


class PaperError(ValueError):
    """Ledger refused a simulated fill."""


def stop_fill_price(stop: Decimal, open_: Decimal, low: Decimal) -> Decimal | None:
    """Paper stop, checked on every candle, including outside the entry window.

    A long is stopped when the bar trades at or through `stop`. If the bar
    opens through the stop, the fill is the open (the gap). Otherwise the
    fill is the stop. The swing may stay open 1 to 5 days; this check does
    not wait for 10:00–12:30.
    """
    stop = _D(stop)
    open_ = _D(open_)
    low = _D(low)
    if open_ <= stop:
        return open_
    if low <= stop:
        return stop
    return None


def _D(value: Decimal | int | str) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def _dec_str(value: Decimal) -> str:
    return format(value, "f")


@dataclass
class Position:
    symbol: str
    qty: Decimal
    entry: Decimal
    stop: Decimal
    target: Decimal
    entry_fee: Decimal
    opened_at: str

    def to_json(self) -> dict[str, str]:
        return {
            "symbol": self.symbol,
            "side": "Buy",
            "qty": _dec_str(self.qty),
            "entry": _dec_str(self.entry),
            "stop": _dec_str(self.stop),
            "target": _dec_str(self.target),
            "entry_fee": _dec_str(self.entry_fee),
            "opened_at": self.opened_at,
        }

    @classmethod
    def from_json(cls, payload: dict[str, str]) -> Position:
        if payload.get("side", "Buy") != "Buy":
            raise PaperError("ledger contains a non-long position; this desk is long-only")
        return cls(
            symbol=payload["symbol"],
            qty=_D(payload["qty"]),
            entry=_D(payload["entry"]),
            stop=_D(payload["stop"]),
            target=_D(payload["target"]),
            entry_fee=_D(payload["entry_fee"]),
            opened_at=payload["opened_at"],
        )


@dataclass
class ClosedTrade:
    symbol: str
    qty: Decimal
    entry: Decimal
    exit_price: Decimal
    entry_fee: Decimal
    exit_fee: Decimal
    pnl: Decimal
    opened_at: str
    closed_at: str

    def to_json(self) -> dict[str, str]:
        return {
            "symbol": self.symbol,
            "qty": _dec_str(self.qty),
            "entry": _dec_str(self.entry),
            "exit": _dec_str(self.exit_price),
            "entry_fee": _dec_str(self.entry_fee),
            "exit_fee": _dec_str(self.exit_fee),
            "pnl": _dec_str(self.pnl),
            "opened_at": self.opened_at,
            "closed_at": self.closed_at,
        }

    @classmethod
    def from_json(cls, payload: dict[str, str]) -> ClosedTrade:
        return cls(
            symbol=payload["symbol"],
            qty=_D(payload["qty"]),
            entry=_D(payload["entry"]),
            exit_price=_D(payload["exit"]),
            entry_fee=_D(payload["entry_fee"]),
            exit_fee=_D(payload["exit_fee"]),
            pnl=_D(payload["pnl"]),
            opened_at=payload["opened_at"],
            closed_at=payload["closed_at"],
        )


@dataclass
class Ledger:
    starting_equity: Decimal
    cash: Decimal
    fee_rate: Decimal = VIP0_SIDE_FEE
    position: Position | None = None
    trades: list[ClosedTrade] | None = None
    quote: str = "USDT"

    def __post_init__(self) -> None:
        if self.trades is None:
            self.trades = []

    def marked_equity(self, mark: Decimal | None = None) -> Decimal:
        """Cash plus the long, net of the exit fee if it were sold at `mark`."""
        if self.position is None:
            return self.cash
        if mark is None:
            raise PaperError("a mark price is required while a position is open")
        return self.cash + self.position.qty * mark * (Decimal("1") - self.fee_rate)

    def _closed_today(self, now: datetime | None) -> list[ClosedTrade]:
        """Closes on the same America/Sao_Paulo calendar day."""
        if now is None or not self.trades:
            return []
        day = sao_paulo_now(now).date()
        found: list[ClosedTrade] = []
        for trade in self.trades:
            closed = datetime.fromisoformat(trade.closed_at)
            if closed.tzinfo is None:
                closed = closed.replace(tzinfo=timezone.utc)
            if closed.astimezone(sao_paulo_now(now).tzinfo).date() == day:
                found.append(trade)
        return found

    def losses_today(self, now: datetime | None) -> int:
        """Losing closes on the same America/Sao_Paulo calendar day."""
        return sum(1 for trade in self._closed_today(now) if trade.pnl < 0)

    def trades_today(self, now: datetime | None) -> int:
        """Closed trades on the same America/Sao_Paulo calendar day."""
        return len(self._closed_today(now))

    def account(self, equity: Decimal | None = None, now: datetime | None = None) -> AccountSnapshot:
        marked = self.cash if equity is None else equity
        return AccountSnapshot(
            equity=marked,
            starting_equity=self.starting_equity,
            open_positions=0 if self.position is None else 1,
            fee_rate=self.fee_rate,
            losses_today=self.losses_today(now),
            trades_today=self.trades_today(now),
        )

    def to_json(self) -> dict:
        return {
            "version": 1,
            "quote": self.quote,
            "fee_rate": _dec_str(self.fee_rate),
            "starting_equity": _dec_str(self.starting_equity),
            "cash": _dec_str(self.cash),
            "position": None if self.position is None else self.position.to_json(),
            "trades": [trade.to_json() for trade in (self.trades or [])],
        }

    @classmethod
    def from_json(cls, payload: dict) -> Ledger:
        if payload.get("version") != 1:
            raise PaperError("unsupported ledger version")
        if payload.get("quote", "USDT") != "USDT":
            raise PaperError("paper ledger quote must be USDT")
        position = payload.get("position")
        trades = [ClosedTrade.from_json(item) for item in payload.get("trades", [])]
        return cls(
            starting_equity=_D(payload["starting_equity"]),
            cash=_D(payload["cash"]),
            fee_rate=_D(payload.get("fee_rate", "0.001")),
            position=None if position is None else Position.from_json(position),
            trades=trades,
            quote="USDT",
        )


def default_ledger(starting_equity: Decimal = Decimal("20"), fee_rate: Decimal = VIP0_SIDE_FEE) -> Ledger:
    starting_equity = _D(starting_equity)
    return Ledger(starting_equity=starting_equity, cash=starting_equity, fee_rate=_D(fee_rate))


def ledger_writes_enabled(writer: bool | None = None) -> bool:
    """File writes require LEDGER_WRITER=1. Anything else is read-only."""
    if writer is not None:
        return writer
    return os.environ.get(LEDGER_WRITER_ENV, "").strip() == "1"


def load_ledger(path: str | Path) -> Ledger:
    file_path = Path(path)
    if not file_path.is_file():
        raise PaperError(f"no ledger at {file_path}")
    fd = os.open(file_path, os.O_RDONLY)
    try:
        fcntl.flock(fd, fcntl.LOCK_SH)
        chunks: list[bytes] = []
        while True:
            block = os.read(fd, 65536)
            if not block:
                break
            chunks.append(block)
    finally:
        fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)
    return Ledger.from_json(json.loads(b"".join(chunks).decode("utf-8")))


def save_ledger(ledger: Ledger, path: str | Path, *, writer: bool | None = None) -> None:
    """Exclusive file lock. Refuses unless LEDGER_WRITER=1 (or writer=True in tests)."""
    if not ledger_writes_enabled(writer):
        raise PaperError("ledger is read-only; set LEDGER_WRITER=1 to write")
    file_path = Path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    payload = (json.dumps(ledger.to_json(), indent=2) + "\n").encode("utf-8")
    fd = os.open(file_path, os.O_RDWR | os.O_CREAT, 0o644)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        os.ftruncate(fd, 0)
        os.lseek(fd, 0, os.SEEK_SET)
        os.write(fd, payload)
        os.fsync(fd)
    finally:
        fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)


def load_or_default(path: str | Path, starting_equity: Decimal = Decimal("20")) -> tuple[Ledger, bool]:
    """Return the ledger and whether it was read from disk."""
    file_path = Path(path)
    if file_path.is_file():
        return load_ledger(file_path), True
    return default_ledger(starting_equity), False


def _now_iso(now: datetime | None) -> str:
    moment = now or datetime.now(timezone.utc)
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return moment.astimezone(timezone.utc).isoformat()


@dataclass(frozen=True)
class PaperAction:
    """Result of a paper mutation. Dry-run leaves the ledger untouched."""

    decision: GateDecision | None
    applied: bool
    dry_run: bool
    trade: ClosedTrade | None = None
    event: EventAction | None = None


def open_long(
    ledger: Ledger,
    plan: OrderPlan,
    now: datetime | None = None,
    requested_qty: Decimal | None = None,
    *,
    writer: bool | None = None,
    path: str | Path | None = None,
    entry_locked: bool = False,
    entry_lock_reason: str = "",
    events: tuple[MacroEvent, ...] = (),
) -> PaperAction:
    """Simulate a spot buy if the risk gate allows it. No exchange call.

    Default is dry-run: the ledger object and the file stay unchanged.
    Set writer=True or LEDGER_WRITER=1 to apply. A path write takes an exclusive lock.
    """
    if ledger.position is not None:
        raise PaperError("max 1 open position")
    decision = evaluate(
        plan,
        ledger.account(ledger.cash, now),
        requested_qty=requested_qty,
        now=now,
        events=events,
        entry_locked=entry_locked,
        entry_lock_reason=entry_lock_reason,
    )
    if not decision.allowed:
        raise PaperError(decision.summary)
    if not ledger_writes_enabled(writer):
        return PaperAction(decision=decision, applied=False, dry_run=True)
    _apply_open(ledger, plan, decision, now)
    if path is not None:
        save_ledger(ledger, path, writer=True)
    return PaperAction(decision=decision, applied=True, dry_run=False)


def _apply_open(ledger: Ledger, plan: OrderPlan, decision: GateDecision, now: datetime | None) -> None:
    qty = decision.qty
    debit = qty * plan.entry * (Decimal("1") + ledger.fee_rate)
    if debit > ledger.cash:
        raise PaperError("insufficient paper cash")
    fee = qty * plan.entry * ledger.fee_rate
    ledger.cash -= debit
    ledger.position = Position(
        symbol=plan.symbol,
        qty=qty,
        entry=plan.entry,
        stop=plan.stop,
        target=plan.target,
        entry_fee=fee,
        opened_at=_now_iso(now),
    )


def close_long(
    ledger: Ledger,
    exit_price: Decimal,
    now: datetime | None = None,
    *,
    writer: bool | None = None,
    path: str | Path | None = None,
) -> PaperAction:
    """Simulate a spot sell. Dry-run unless LEDGER_WRITER=1. No exchange call."""
    if ledger.position is None:
        raise PaperError("no open position")
    exit_price = _D(exit_price)
    if exit_price <= 0:
        raise PaperError("exit price must be positive")
    trade = _trade_at(ledger, exit_price, now)
    if not ledger_writes_enabled(writer):
        return PaperAction(decision=None, applied=False, dry_run=True, trade=trade)
    _apply_close(ledger, trade)
    if path is not None:
        save_ledger(ledger, path, writer=True)
    return PaperAction(decision=None, applied=True, dry_run=False, trade=trade)


def _trade_at(ledger: Ledger, exit_price: Decimal, now: datetime | None) -> ClosedTrade:
    assert ledger.position is not None
    position = ledger.position
    exit_fee = position.qty * exit_price * ledger.fee_rate
    credit = position.qty * exit_price * (Decimal("1") - ledger.fee_rate)
    pnl = credit - (position.qty * position.entry + position.entry_fee)
    return ClosedTrade(
        symbol=position.symbol,
        qty=position.qty,
        entry=position.entry,
        exit_price=exit_price,
        entry_fee=position.entry_fee,
        exit_fee=exit_fee,
        pnl=pnl,
        opened_at=position.opened_at,
        closed_at=_now_iso(now),
    )


def _apply_close(ledger: Ledger, trade: ClosedTrade) -> None:
    assert ledger.position is not None
    credit = trade.qty * trade.exit_price * (Decimal("1") - ledger.fee_rate)
    ledger.cash += credit
    assert ledger.trades is not None
    ledger.trades.append(trade)
    ledger.position = None


def manage_into_event(
    ledger: Ledger,
    mark: Decimal,
    now: datetime,
    events: tuple[MacroEvent, ...] = (),
    *,
    writer: bool | None = None,
    path: str | Path | None = None,
) -> PaperAction:
    """Paper-only pre-event action. Dry-run unless the writer flag is on."""
    if ledger.position is None:
        action = EventAction("none", "flat")
        return PaperAction(decision=None, applied=False, dry_run=not ledger_writes_enabled(writer), event=action)
    position = ledger.position
    action = pre_event_action(
        entry=position.entry,
        stop=position.stop,
        mark=mark,
        now=now,
        events=events,
    )
    if action.kind == "none" or not ledger_writes_enabled(writer):
        return PaperAction(
            decision=None,
            applied=False,
            dry_run=not ledger_writes_enabled(writer),
            event=action,
        )
    if action.kind == "close":
        closed = close_long(ledger, mark, now, writer=True, path=path)
        return PaperAction(
            decision=closed.decision,
            applied=True,
            dry_run=False,
            trade=closed.trade,
            event=action,
        )
    if action.kind == "raise_stop" and action.new_stop is not None:
        position.stop = action.new_stop
        if path is not None:
            save_ledger(ledger, path, writer=True)
        return PaperAction(decision=None, applied=True, dry_run=False, event=action)
    return PaperAction(decision=None, applied=False, dry_run=False, event=action)
