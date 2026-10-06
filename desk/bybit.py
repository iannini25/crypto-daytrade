"""Bybit public market data.

Only three GET routes are implemented:

- /v5/market/tickers
- /v5/market/kline
- /v5/market/orderbook

Category is forced to spot. Requests carry no API key and no signature.
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from decimal import Decimal
from typing import Callable

INTERVAL_MS = {
    "15": 15 * 60 * 1000,
    "60": 60 * 60 * 1000,
    "D": 24 * 60 * 60 * 1000,
}

Transport = Callable[..., object]


class BybitError(RuntimeError):
    """Public REST call failed or returned an unexpected body."""


@dataclass(frozen=True)
class Ticker:
    symbol: str
    last: Decimal
    bid: Decimal
    ask: Decimal
    turnover24h: Decimal
    volume24h: Decimal

    @property
    def spread_bps(self) -> Decimal:
        mid = (self.bid + self.ask) / 2
        if mid <= 0:
            return Decimal("0")
        return (self.ask - self.bid) / mid * Decimal("10000")


@dataclass(frozen=True)
class Candle:
    start_ms: int
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal
    turnover: Decimal


@dataclass(frozen=True)
class OrderBook:
    symbol: str
    bid: Decimal
    ask: Decimal
    bid_size: Decimal
    ask_size: Decimal

    @property
    def spread_bps(self) -> Decimal:
        mid = (self.bid + self.ask) / 2
        if mid <= 0:
            return Decimal("0")
        return (self.ask - self.bid) / mid * Decimal("10000")


def _decimal(value: object) -> Decimal:
    return Decimal(str(value))


class BybitPublicClient:
    """Read-only spot client. Constructing it cannot place an order."""

    def __init__(
        self,
        base_url: str = "https://api.bybit.com",
        timeout: float = 15.0,
        transport: Transport | None = None,
    ) -> None:
        if not base_url.startswith("https://"):
            raise BybitError("base URL must be https")
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._transport = transport or urllib.request.urlopen

    def ticker(self, symbol: str) -> Ticker:
        payload = self._get("/v5/market/tickers", {"category": "spot", "symbol": symbol})
        rows = payload.get("result", {}).get("list") or []
        if not rows:
            raise BybitError(f"no ticker for {symbol}")
        row = rows[0]
        return Ticker(
            symbol=str(row["symbol"]),
            last=_decimal(row["lastPrice"]),
            bid=_decimal(row["bid1Price"]),
            ask=_decimal(row["ask1Price"]),
            turnover24h=_decimal(row.get("turnover24h", "0")),
            volume24h=_decimal(row.get("volume24h", "0")),
        )

    def klines(self, symbol: str, interval: str, limit: int = 200, now_ms: int | None = None) -> list[Candle]:
        if interval not in INTERVAL_MS:
            raise BybitError(f"unsupported interval {interval}; use 15, 60, or D")
        if limit < 1 or limit > 1000:
            raise BybitError("kline limit must be between 1 and 1000")
        payload = self._get(
            "/v5/market/kline",
            {"category": "spot", "symbol": symbol, "interval": interval, "limit": str(limit)},
        )
        rows = payload.get("result", {}).get("list") or []
        # Bybit returns the newest candle first.
        candles = [self._candle(row) for row in reversed(rows)]
        moment = int(time.time() * 1000) if now_ms is None else now_ms
        if candles and candles[-1].start_ms + INTERVAL_MS[interval] > moment:
            candles = candles[:-1]
        return candles

    def orderbook(self, symbol: str, limit: int = 25) -> OrderBook:
        if limit < 1 or limit > 200:
            raise BybitError("orderbook limit must be between 1 and 200")
        payload = self._get(
            "/v5/market/orderbook",
            {"category": "spot", "symbol": symbol, "limit": str(limit)},
        )
        result = payload.get("result") or {}
        bids = result.get("b") or []
        asks = result.get("a") or []
        if not bids or not asks:
            raise BybitError(f"empty orderbook for {symbol}")
        return OrderBook(
            symbol=str(result.get("s") or symbol),
            bid=_decimal(bids[0][0]),
            ask=_decimal(asks[0][0]),
            bid_size=_decimal(bids[0][1]),
            ask_size=_decimal(asks[0][1]),
        )

    def _candle(self, row: list) -> Candle:
        # [start, open, high, low, close, volume, turnover]
        if len(row) < 6:
            raise BybitError("kline row is short")
        return Candle(
            start_ms=int(row[0]),
            open=_decimal(row[1]),
            high=_decimal(row[2]),
            low=_decimal(row[3]),
            close=_decimal(row[4]),
            volume=_decimal(row[5]),
            turnover=_decimal(row[6]) if len(row) > 6 else Decimal("0"),
        )

    def _get(self, path: str, params: dict[str, str]) -> dict:
        if params.get("category") != "spot":
            raise BybitError("public client refuses any category other than spot")
        if path not in {"/v5/market/tickers", "/v5/market/kline", "/v5/market/orderbook"}:
            raise BybitError(f"path is not a public market route: {path}")
        query = urllib.parse.urlencode(params)
        url = f"{self.base_url}{path}?{query}"
        request = urllib.request.Request(
            url,
            method="GET",
            headers={
                "Accept": "application/json",
                "User-Agent": "crypto-daytrade-paper/0.1",
            },
        )
        last_error: Exception | None = None
        for attempt in range(2):
            try:
                with self._transport(request, timeout=self.timeout) as response:
                    body = response.read()
                break
            except urllib.error.HTTPError as exc:
                detail = exc.read().decode("utf-8", errors="replace")
                if exc.code == 403 and "block access from your country" in detail.lower():
                    raise BybitError(
                        "Bybit refused this network (CloudFront country block). "
                        "Run snapshot and scan from a region Bybit serves; a home link in Brazil does. "
                        "This is not a missing API key."
                    ) from exc
                raise BybitError(f"HTTP {exc.code} for {path}: {detail[:300]}") from exc
            except (urllib.error.URLError, TimeoutError, OSError) as exc:
                last_error = exc
                if attempt == 0:
                    time.sleep(0.4)
                    continue
                raise BybitError(f"network error for {path}: {exc}") from exc
        else:
            raise BybitError(f"network error for {path}: {last_error}")
        try:
            payload = json.loads(body.decode("utf-8"))
        except json.JSONDecodeError as exc:
            raise BybitError(f"non-JSON response from {path}") from exc
        if payload.get("retCode") != 0:
            raise BybitError(f"Bybit retCode {payload.get('retCode')}: {payload.get('retMsg')}")
        return payload
