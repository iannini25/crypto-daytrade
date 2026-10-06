"""Simulated USDT ledger.

Fills exist only in a local JSON file. Nothing here talks to Bybit.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

from desk.fees import VIP0_SIDE_FEE
from desk.risk import AccountSnapshot, GateDecision, OrderPlan, evaluate


class PaperError(ValueError):
    """Ledger refused a simulated fill."""


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

    def account(self, equity: Decimal | None = None) -> AccountSnapshot:
        marked = self.cash if equity is None else equity
        return AccountSnapshot(
            equity=marked,
            starting_equity=self.starting_equity,
            open_positions=0 if self.position is None else 1,
            fee_rate=self.fee_rate,
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


def load_ledger(path: str | Path) -> Ledger:
    file_path = Path(path)
    if not file_path.is_file():
        raise PaperError(f"no ledger at {file_path}")
    return Ledger.from_json(json.loads(file_path.read_text(encoding="utf-8")))


def save_ledger(ledger: Ledger, path: str | Path) -> None:
    file_path = Path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(json.dumps(ledger.to_json(), indent=2) + "\n", encoding="utf-8")


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


def open_long(
    ledger: Ledger,
    plan: OrderPlan,
    now: datetime | None = None,
    requested_qty: Decimal | None = None,
) -> GateDecision:
    """Simulate a spot buy if the risk gate allows it. No exchange call."""
    if ledger.position is not None:
        raise PaperError("max 1 open position")
    decision = evaluate(plan, ledger.account(ledger.cash), requested_qty=requested_qty)
    if not decision.allowed:
        raise PaperError(decision.summary)
    assert decision.net_risk_per_unit is not None
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
    return decision


def close_long(ledger: Ledger, exit_price: Decimal, now: datetime | None = None) -> ClosedTrade:
    """Simulate a spot sell at `exit_price`. No exchange call."""
    if ledger.position is None:
        raise PaperError("no open position")
    exit_price = _D(exit_price)
    if exit_price <= 0:
        raise PaperError("exit price must be positive")
    position = ledger.position
    exit_fee = position.qty * exit_price * ledger.fee_rate
    credit = position.qty * exit_price * (Decimal("1") - ledger.fee_rate)
    ledger.cash += credit
    pnl = credit - (position.qty * position.entry + position.entry_fee)
    trade = ClosedTrade(
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
    assert ledger.trades is not None
    ledger.trades.append(trade)
    ledger.position = None
    return trade
