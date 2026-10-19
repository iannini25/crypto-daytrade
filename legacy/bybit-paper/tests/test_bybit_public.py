"""Public client: spot GETs, no credentials, unfinished candle dropped."""

import io
import json
import urllib.error
from decimal import Decimal

import pytest

from desk.bybit import BybitError, BybitPublicClient


class _Response:
    def __init__(self, body: bytes) -> None:
        self._body = body

    def read(self) -> bytes:
        return self._body

    def __enter__(self) -> "_Response":
        return self

    def __exit__(self, *_args) -> bool:
        return False


class _Transport:
    def __init__(self, payload: dict) -> None:
        self.payload = payload
        self.requests = []

    def __call__(self, request, timeout):
        self.requests.append((request, timeout))
        return _Response(json.dumps(self.payload).encode())


def test_ticker_is_a_public_spot_get():
    transport = _Transport(
        {
            "retCode": 0,
            "retMsg": "OK",
            "result": {
                "list": [
                    {
                        "symbol": "BTCUSDT",
                        "lastPrice": "65000",
                        "bid1Price": "64999",
                        "ask1Price": "65001",
                        "turnover24h": "1000",
                        "volume24h": "10",
                    }
                ]
            },
        }
    )
    client = BybitPublicClient(transport=transport)
    ticker = client.ticker("BTCUSDT")
    assert ticker.last == Decimal("65000")
    assert ticker.spread_bps > 0
    request, _timeout = transport.requests[0]
    assert request.get_method() == "GET"
    assert "/v5/market/tickers?" in request.full_url
    assert "category=spot" in request.full_url
    assert "symbol=BTCUSDT" in request.full_url
    names = {key.lower() for key, _value in request.header_items()}
    assert "x-bapi-api-key" not in names
    assert "x-bapi-sign" not in names


def test_klines_drop_the_open_candle_and_reverse():
    transport = _Transport(
        {
            "retCode": 0,
            "result": {
                "list": [
                    ["1700001800000", "3", "4", "2", "3.5", "1", "2"],
                    ["1700000900000", "2", "3", "1", "2.5", "1", "2"],
                    ["1700000000000", "1", "2", "1", "1.5", "1", "2"],
                ]
            },
        }
    )
    client = BybitPublicClient(transport=transport)
    # 15m candles. The newest starts at 1700001800000 and is still open at +1 ms.
    candles = client.klines("ETHUSDT", "15", limit=3, now_ms=1700001800000 + 1)
    assert [candle.close for candle in candles] == [Decimal("1.5"), Decimal("2.5")]
    assert "/v5/market/kline?" in transport.requests[0][0].full_url
    assert "interval=15" in transport.requests[0][0].full_url


def test_orderbook_and_refuses_non_public_paths():
    transport = _Transport(
        {"retCode": 0, "result": {"s": "SOLUSDT", "b": [["100", "2"]], "a": [["100.1", "3"]]}}
    )
    client = BybitPublicClient(transport=transport)
    book = client.orderbook("SOLUSDT", limit=5)
    assert book.bid == Decimal("100")
    assert book.ask == Decimal("100.1")
    with pytest.raises(BybitError, match="not a public market route"):
        client._get("/v5/order/create", {"category": "spot"})
    with pytest.raises(BybitError):
        client._get("/v5/market/tickers", {"category": "linear", "symbol": "BTCUSDT"})


def test_country_block_is_not_reported_as_an_auth_error():
    def transport(request, timeout):
        raise urllib.error.HTTPError(
            request.full_url,
            403,
            "Forbidden",
            hdrs=None,
            fp=io.BytesIO(b"{ error: The Amazon CloudFront distribution is configured to block access from your country }"),
        )

    client = BybitPublicClient(transport=transport)
    with pytest.raises(BybitError, match="country block") as raised:
        client.ticker("BTCUSDT")
    assert "API key" in str(raised.value)
