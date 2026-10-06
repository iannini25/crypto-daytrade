"""Command line monitors.

snapshot and scan read public Bybit market data.
paper-status reads the local simulated ledger.
None of them place orders.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

from desk import __version__
from desk.bybit import BybitError, BybitPublicClient
from desk.config import ConfigError, load_config
from desk.events import hold_horizon, load_events, pre_event_action
from desk.paper import PaperError, ledger_writes_enabled, load_or_default, save_ledger
from desk.risk import AccountSnapshot, stop_bands
from desk.scanner import ScanRow, analyze
from desk.session import in_liquidity_window, sao_paulo_now

NO_ORDERS = "No orders sent. This desk has no live order placement."


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="desk",
        description="Paper-only Bybit spot monitors. These commands never place orders.",
    )
    parser.add_argument("--version", action="version", version=f"desk {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    snap = sub.add_parser("snapshot", help="Public 15m and 1d snapshot for BTC, ETH, and SOL")
    snap.add_argument("--json", action="store_true")

    status = sub.add_parser("paper-status", help="Show the simulated ledger and risk limits")
    status.add_argument("--json", action="store_true")
    status.add_argument("--init", action="store_true", help="Write a fresh ledger if the file is absent")
    status.add_argument("--ledger", default=None, help="Override DESK_LEDGER_PATH")

    scan = sub.add_parser("scan", help="Dry-run long-only pattern scan. Never posts orders")
    scan.add_argument("--json", action="store_true")
    scan.add_argument("--ledger", default=None, help="Override DESK_LEDGER_PATH")

    args = parser.parse_args(argv)
    try:
        config = load_config()
    except ConfigError as exc:
        print(f"config: {exc}", file=sys.stderr)
        return 2

    if args.command == "snapshot":
        return _snapshot(config, as_json=args.json)
    if args.command == "paper-status":
        return _paper_status(config, as_json=args.json, init=args.init, ledger=args.ledger)
    if args.command == "scan":
        return _scan(config, as_json=args.json, ledger=args.ledger)
    print(f"unknown command {args.command}", file=sys.stderr)
    return 2


def _snapshot(config, as_json: bool) -> int:
    now = datetime.now(timezone.utc)
    client = BybitPublicClient(base_url=config.base_url)
    try:
        rows = collect_snapshot(client, config.symbols, now_ms=int(now.timestamp() * 1000))
    except BybitError as exc:
        print(f"bybit: {exc}", file=sys.stderr)
        return 1
    payload = {
        "command": "snapshot",
        "as_of_sao_paulo": sao_paulo_now(now).isoformat(timespec="seconds"),
        "liquidity_window_open": in_liquidity_window(now),
        "category": "spot",
        "orders_sent": False,
        "rows": rows,
    }
    print(_dump(payload) if as_json else render_snapshot(payload))
    return 0


def collect_snapshot(client: BybitPublicClient, symbols: tuple[str, ...], now_ms: int) -> list[dict]:
    rows: list[dict] = []
    for symbol in symbols:
        ticker = client.ticker(symbol)
        book = client.orderbook(symbol)
        m15 = client.klines(symbol, "15", limit=5, now_ms=now_ms)
        daily = client.klines(symbol, "D", limit=5, now_ms=now_ms)
        if not m15 or not daily:
            raise BybitError(f"not enough closed candles for {symbol}")
        rows.append(
            {
                "symbol": symbol,
                "last": ticker.last,
                "bid": book.bid,
                "ask": book.ask,
                "bid_size": book.bid_size,
                "ask_size": book.ask_size,
                "spread_bps": book.spread_bps,
                "turnover24h": ticker.turnover24h,
                "m15_close": m15[-1].close,
                "m15_start_ms": m15[-1].start_ms,
                "daily_close": daily[-1].close,
                "daily_start_ms": daily[-1].start_ms,
            }
        )
    return rows


def render_snapshot(payload: dict) -> str:
    window = "OPEN" if payload["liquidity_window_open"] else "CLOSED"
    lines = [
        f"snapshot {payload['as_of_sao_paulo']}  America/Sao_Paulo  liquidity window {window}",
        "spot public data only. Round-trip cost 0.30% (VIP0 0.20% + 0.10% slippage). No orders.",
        f"{'symbol':<10} {'last':>14} {'bid':>14} {'ask':>14} {'spread_bps':>10} "
        f"{'15m_close':>14} {'1d_close':>14} {'turnover24h':>16}",
    ]
    for row in payload["rows"]:
        lines.append(
            f"{row['symbol']:<10} {_px(row['last']):>14} {_px(row['bid']):>14} {_px(row['ask']):>14} "
            f"{_px(row['spread_bps']):>10} {_px(row['m15_close']):>14} {_px(row['daily_close']):>14} "
            f"{_px(row['turnover24h']):>16}"
        )
    lines.append(NO_ORDERS)
    return "\n".join(lines) + "\n"


def _paper_status(config, as_json: bool, init: bool, ledger: str | None) -> int:
    path = Path(ledger or config.ledger_path)
    try:
        book, persisted = load_or_default(path, config.paper_equity_usdt)
    except (PaperError, json.JSONDecodeError, OSError) as exc:
        print(f"ledger: {exc}", file=sys.stderr)
        return 2
    writer_note = None
    if init and not persisted:
        if ledger_writes_enabled():
            save_ledger(book, path)
            persisted = True
        else:
            writer_note = "dry-run: ledger not written (set LEDGER_WRITER=1)"
    mark = None
    mark_note = None
    if book.position is not None:
        try:
            mark = BybitPublicClient(base_url=config.base_url).ticker(book.position.symbol).last
        except BybitError as exc:
            mark_note = f"mark unavailable: {exc}"
    equity = book.cash if mark is None and book.position is None else None
    if book.position is not None and mark is not None:
        equity = book.marked_equity(mark)
    kill_line = book.starting_equity * config.kill_ratio
    payload = {
        "command": "paper-status",
        "persisted": persisted,
        "ledger_path": str(path),
        "quote": "USDT",
        "cash": book.cash,
        "starting_equity": book.starting_equity,
        "marked_equity": equity,
        "mark": mark,
        "mark_note": mark_note,
        "brl_per_usdt_hint": config.brl_per_usdt,
        "illustrative_brl": None if equity is None else equity * config.brl_per_usdt,
        "kill_equity": kill_line,
        "kill_active": equity is not None and equity <= kill_line,
        "open_positions": 0 if book.position is None else 1,
        "position": None if book.position is None else book.position.to_json(),
        "closed_trades": len(book.trades or []),
        "fee_rate_per_side": book.fee_rate,
        "round_trip_fee": book.fee_rate * 2,
        "round_trip_cost": Decimal("0.003"),
        "max_risk": config.max_risk,
        "risk_cap": config.risk_cap,
        "min_order_usdt": config.min_order_usdt,
        "min_rr_after_fees": config.min_rr,
        "max_positions": config.max_positions,
        "ledger_writer": ledger_writes_enabled(),
        "writer_note": writer_note,
        "losses_today": book.losses_today(datetime.now(timezone.utc)),
        "trades_today": book.trades_today(datetime.now(timezone.utc)),
        "api_key_set": config.api_key_set,
        "api_secret_set": config.api_secret_set,
        "ai_subaccount_set": config.ai_subaccount_set,
        "live_orders_confirm": config.live_orders_confirm,
        "live_order_placement": "disabled",
        "orders_sent": False,
    }
    bands = stop_bands(
        equity if equity is not None else book.cash,
        fee_rate=book.fee_rate,
        min_order_usdt=config.min_order_usdt,
        target_risk=config.max_risk,
        risk_cap=config.risk_cap,
    )
    payload["min_stop_percent"] = bands.min_stop_percent
    payload["target_zone_max_percent"] = bands.target_zone_max_percent
    payload["cap_stop_percent"] = bands.cap_stop_percent
    if book.position is not None:
        opened = datetime.fromisoformat(book.position.opened_at)
        if opened.tzinfo is None:
            opened = opened.replace(tzinfo=timezone.utc)
        payload["hold"] = hold_horizon(opened, datetime.now(timezone.utc))
        events = load_events(config.events_path)
        if mark is not None:
            risk_stop = book.position.stop_initial or book.position.stop
            if risk_stop >= book.position.entry:
                risk_stop = book.position.stop
            action = pre_event_action(
                entry=book.position.entry,
                stop=risk_stop,
                mark=mark,
                now=datetime.now(timezone.utc),
                events=events,
            )
            payload["event_action"] = action.kind
            payload["event_note"] = action.reason
        else:
            payload["event_action"] = None
            payload["event_note"] = mark_note
    print(_dump(payload) if as_json else render_paper_status(payload))
    return 0


def render_paper_status(payload: dict) -> str:
    equity = payload["marked_equity"]
    equity_text = "unknown (no mark)" if equity is None else f"{_px(equity)} USDT"
    brl = payload["illustrative_brl"]
    brl_text = "n/a" if brl is None else f"about R$ {_px(brl)} at the hint rate, not a live FX quote"
    lines = [
        f"paper ledger {payload['ledger_path']}  persisted={payload['persisted']}",
        f"cash {_px(payload['cash'])} USDT   marked equity {equity_text}",
        f"starting {_px(payload['starting_equity'])} USDT   kill at or below {_px(payload['kill_equity'])} USDT"
        f"   kill_active={payload['kill_active']}",
        f"illustrative BRL: {brl_text}",
        f"open positions {payload['open_positions']} (max {payload['max_positions']})   "
        f"closed trades {payload['closed_trades']}",
        f"fees {_px(payload['fee_rate_per_side'])} per side ({_px(payload['round_trip_fee'])} round trip) "
        f"plus slippage, cost {_px(payload['round_trip_cost'])}",
        f"stop bands: min {_px(payload['min_stop_percent'])}%  "
        f"1% zone <= {_px(payload['target_zone_max_percent'])}%  "
        f"cap {_px(payload['cap_stop_percent'])}%  min order {_px(payload['min_order_usdt'])} USDT",
        f"target risk {_px(payload['max_risk'])}  cap {_px(payload['risk_cap'])}  "
        f"min net R:R {_px(payload['min_rr_after_fees'])}  "
        f"losses today {payload['losses_today']}  trades today {payload['trades_today']}",
        f"ledger_writer={payload['ledger_writer']}",
        f"api_key_set={payload['api_key_set']} api_secret_set={payload['api_secret_set']} "
        f"ai_subaccount_set={payload['ai_subaccount_set']}",
        f"LIVE_ORDERS_CONFIRM={payload['live_orders_confirm']}  live_order_placement=disabled",
    ]
    if payload.get("writer_note"):
        lines.append(payload["writer_note"])
    if payload["mark_note"]:
        lines.append(payload["mark_note"])
    if payload["position"]:
        position = payload["position"]
        lines.append(
            f"position {position['symbol']} qty {position['qty']} entry {position['entry']} "
            f"stop {position['stop']} target {position['target']}"
        )
    else:
        lines.append("position flat")
    if payload.get("hold"):
        lines.append(f"hold {payload['hold']} (overnight allowed, swing horizon 1-5 days)")
    if payload.get("event_note"):
        lines.append(f"event: {payload['event_note']}")
    lines.append("Funding path for a real account is a human Pix deposit in BRL. This process does not move money.")
    lines.append(NO_ORDERS)
    return "\n".join(lines) + "\n"


def _scan(config, as_json: bool, ledger: str | None) -> int:
    path = Path(ledger or config.ledger_path)
    try:
        book, _persisted = load_or_default(path, config.paper_equity_usdt)
    except (PaperError, json.JSONDecodeError, OSError) as exc:
        print(f"ledger: {exc}", file=sys.stderr)
        return 2
    now = datetime.now(timezone.utc)
    client = BybitPublicClient(base_url=config.base_url)
    equity = book.cash
    if book.position is not None:
        try:
            mark = client.ticker(book.position.symbol).last
        except BybitError as exc:
            print(f"bybit: cannot mark open paper position: {exc}", file=sys.stderr)
            return 1
        equity = book.marked_equity(mark)
    account = AccountSnapshot(
        equity=equity,
        starting_equity=book.starting_equity,
        open_positions=0 if book.position is None else 1,
        fee_rate=book.fee_rate,
        max_risk=config.max_risk,
        risk_cap=config.risk_cap,
        kill_ratio=config.kill_ratio,
        min_rr=config.min_rr,
        max_positions=config.max_positions,
        min_order_usdt=config.min_order_usdt,
        losses_today=book.losses_today(now),
        trades_today=book.trades_today(now),
    )
    try:
        rows = collect_scan(client, config.symbols, account, now, load_events(config.events_path))
    except BybitError as exc:
        print(f"bybit: {exc}", file=sys.stderr)
        return 1
    payload = {
        "command": "scan",
        "as_of_sao_paulo": sao_paulo_now(now).isoformat(timespec="seconds"),
        "liquidity_window_open": in_liquidity_window(now),
        "orders_sent": False,
        "rows": [scan_row_dict(row) for row in rows],
    }
    print(_dump(payload) if as_json else render_scan(payload))
    return 0


def collect_scan(
    client: BybitPublicClient,
    symbols: tuple[str, ...],
    account: AccountSnapshot,
    now: datetime,
    events: tuple = (),
) -> list[ScanRow]:
    now_ms = int(now.timestamp() * 1000)
    rows: list[ScanRow] = []
    for symbol in symbols:
        daily = client.klines(symbol, "D", limit=150, now_ms=now_ms)
        hourly = client.klines(symbol, "60", limit=200, now_ms=now_ms)
        m15 = client.klines(symbol, "15", limit=200, now_ms=now_ms)
        rows.append(analyze(symbol, daily, hourly, m15, account, now, events))
    return rows


def scan_row_dict(row: ScanRow) -> dict:
    payload = asdict(row)
    payload["notes"] = list(row.notes)
    return payload


def render_scan(payload: dict) -> str:
    window = "OPEN" if payload["liquidity_window_open"] else "CLOSED"
    lines = [
        f"scan {payload['as_of_sao_paulo']}  America/Sao_Paulo  liquidity window {window}",
        "Dry run. Pattern on 1h or daily, 15m close only. No orders.",
    ]
    for row in payload["rows"]:
        rr = "n/a" if row["rr_after_fees"] is None else _px(row["rr_after_fees"])
        lines.append(
            f"{row['symbol']:<10} daily_hh_hl={_yes(row['daily_hh_hl']):<3} "
            f"sma100={_yes(row['above_sma100']):<3} "
            f"pattern={row['pattern'] or '-':<28} "
            f"anchor={row['stop_anchor'] or '-':<3} band={row['stop_band']:<12} "
            f"close={_yes(row['close_confirmed']):<3} net_rr={rr:>8} "
            f"{row['disposition']}"
        )
        for note in row["notes"]:
            lines.append(f"           {note}")
    lines.append(NO_ORDERS)
    return "\n".join(lines) + "\n"


def _yes(flag: bool) -> str:
    return "yes" if flag else "no"


def _px(value: Decimal | int | str) -> str:
    number = value if isinstance(value, Decimal) else Decimal(str(value))
    text = format(number, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text or "0"


def _dump(payload: dict) -> str:
    return json.dumps(payload, indent=2, default=_json_default) + "\n"


def _json_default(value: object) -> object:
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, tuple):
        return list(value)
    raise TypeError(f"cannot encode {type(value)!r}")
