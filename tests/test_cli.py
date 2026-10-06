"""Offline CLI paths."""

import json
from decimal import Decimal

from desk.cli import collect_snapshot, main, render_snapshot
from desk.config import parse_dotenv


class _Client:
    def __init__(self) -> None:
        self.calls = []

    def ticker(self, symbol):
        self.calls.append(("ticker", symbol))
        from desk.bybit import Ticker

        return Ticker(symbol, Decimal("10"), Decimal("9.9"), Decimal("10.1"), Decimal("1000"), Decimal("5"))

    def orderbook(self, symbol, limit=25):
        self.calls.append(("book", symbol))
        from desk.bybit import OrderBook

        return OrderBook(symbol, Decimal("9.9"), Decimal("10.1"), Decimal("1"), Decimal("1"))

    def klines(self, symbol, interval, limit=200, now_ms=None):
        self.calls.append(("kline", symbol, interval))
        from desk.bybit import Candle

        return [
            Candle(1_700_000_000_000, Decimal("9"), Decimal("11"), Decimal("8"), Decimal("10"), Decimal("1"), Decimal("1"))
        ]


def test_snapshot_render_uses_only_public_methods(capsys):
    rows = collect_snapshot(_Client(), ("BTCUSDT",), now_ms=1_800_000_000_000)
    text = render_snapshot(
        {
            "as_of_sao_paulo": "2026-10-06T10:30:00-03:00",
            "liquidity_window_open": True,
            "rows": rows,
        }
    )
    assert "BTCUSDT" in text
    assert "No orders sent" in text
    assert "10" in text


def test_paper_status_without_a_file(capsys, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("DESK_LEDGER_PATH", str(tmp_path / "missing.json"))
    monkeypatch.setenv("BYBIT_API_KEY", "")
    monkeypatch.setenv("BYBIT_API_SECRET", "")
    code = main(["paper-status"])
    captured = capsys.readouterr()
    assert code == 0
    assert "live_order_placement=disabled" in captured.out
    assert "No orders sent" in captured.out
    assert "api_key_set=False" in captured.out
    assert not (tmp_path / "missing.json").exists()


def test_paper_status_init_and_json(capsys, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    path = tmp_path / "ledger.json"
    code = main(["paper-status", "--init", "--json", "--ledger", str(path)])
    captured = capsys.readouterr()
    assert code == 0
    payload = json.loads(captured.out)
    assert payload["orders_sent"] is False
    assert payload["live_order_placement"] == "disabled"
    assert payload["persisted"] is True
    assert path.is_file()
    assert Decimal(payload["starting_equity"]) == Decimal("20")


def test_dotenv_parser_keeps_secrets_out_of_the_result_shape():
    parsed = parse_dotenv(
        """
        # comment
        export BYBIT_API_KEY=not-a-real-key
        BYBIT_API_SECRET="not-a-real-secret"
        LIVE_ORDERS_CONFIRM=false
        """
    )
    assert parsed["BYBIT_API_KEY"] == "not-a-real-key"
    assert parsed["LIVE_ORDERS_CONFIRM"] == "false"
    assert parsed["BYBIT_API_SECRET"] == "not-a-real-secret"
