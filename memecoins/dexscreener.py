#!/usr/bin/env python3
"""Read-only DexScreener client.

Public GET requests only. No API key, no wallet, no transaction.
"""

from __future__ import annotations

import json
import sys
import urllib.request

DACITY_MINT = "nxPqZ4F7ux8Vph5NFu25rEP6Kx9Gr1U6Fmj36Rjpump"
DEX = "https://api.dexscreener.com"
USER_AGENT = "iannini-memecoin-desk/1.0 (advisory; read-only)"


class PublicApiError(RuntimeError):
    pass


def get_json(url: str):
    if not url.startswith(DEX + "/"):
        raise PublicApiError(f"refusing non-DexScreener URL: {url}")
    req = urllib.request.Request(
        url,
        method="GET",
        headers={"Accept": "application/json", "User-Agent": USER_AGENT},
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            if resp.status != 200:
                raise PublicApiError(f"HTTP {resp.status} for {url}")
            return json.load(resp)
    except PublicApiError:
        raise
    except Exception as exc:
        raise PublicApiError(str(exc)) from exc


def _num(value):
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str) and value.strip():
        try:
            return float(value)
        except ValueError:
            return None
    return None


def quote_from_pair(pair: dict, mint_hint: str = "") -> dict | None:
    base = pair.get("baseToken") or {}
    mint = base.get("address") or mint_hint
    if not mint:
        return None
    volume = pair.get("volume") or {}
    change = pair.get("priceChange") or {}
    liquidity = pair.get("liquidity") or {}
    return {
        "symbol": base.get("symbol") or "?",
        "name": base.get("name") or "",
        "mint": mint,
        "priceUsd": _num(pair.get("priceUsd")),
        "marketCap": _num(pair.get("marketCap")) if pair.get("marketCap") is not None else _num(pair.get("fdv")),
        "liquidityUsd": _num(liquidity.get("usd")),
        "volumeH24": _num(volume.get("h24")),
        "changeH24": _num(change.get("h24")),
        "url": pair.get("url") or f"https://dexscreener.com/solana/{mint}",
        "dexId": pair.get("dexId") or "",
    }


def best_quote(pairs, mint: str = "") -> dict | None:
    best = None
    for pair in pairs or []:
        if not isinstance(pair, dict):
            continue
        quote = quote_from_pair(pair, mint)
        if not quote:
            continue
        if mint and quote["mint"] != mint:
            continue
        liq = quote["liquidityUsd"] if quote["liquidityUsd"] is not None else -1
        best_liq = -1 if best is None or best["liquidityUsd"] is None else best["liquidityUsd"]
        if best is None or liq > best_liq:
            best = quote
    return best


def pump_mints(rows) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for row in rows or []:
        if not isinstance(row, dict) or row.get("chainId") != "solana":
            continue
        addr = row.get("tokenAddress") or ""
        if not isinstance(addr, str) or not addr.endswith("pump") or addr in seen:
            continue
        seen.add(addr)
        out.append(addr)
    return out


def ranked_pump_mints(top, latest, limit: int = 30) -> list[str]:
    mints = pump_mints(top)
    for mint in pump_mints(latest):
        if mint not in mints:
            mints.append(mint)
    return mints[:limit]


def trending_quotes(top, latest, pairs, limit: int = 10) -> list[dict]:
    mints = ranked_pump_mints(top, latest, max(limit, 30))
    found = []
    for mint in mints:
        quote = best_quote(pairs, mint)
        if quote:
            found.append(quote)
        if len(found) >= limit:
            break
    return found


def dacity() -> dict | None:
    return best_quote(get_json(f"{DEX}/token-pairs/v1/solana/{DACITY_MINT}"), DACITY_MINT)


def trending(limit: int = 10) -> list[dict]:
    top = get_json(f"{DEX}/token-boosts/top/v1")
    latest = get_json(f"{DEX}/token-boosts/latest/v1")
    mints = ranked_pump_mints(top, latest, 30)
    pairs = get_json(f"{DEX}/tokens/v1/solana/{','.join(mints)}") if mints else []
    return trending_quotes(top, latest, pairs, limit)


def main(argv: list[str]) -> int:
    cmd = argv[1] if len(argv) > 1 else "dacity"
    if cmd == "dacity":
        payload = dacity()
    elif cmd == "trending":
        payload = trending()
    else:
        print("usage: dexscreener.py [dacity|trending]", file=sys.stderr)
        return 2
    json.dump(payload, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv))
    except PublicApiError as exc:
        sys.exit(f"dexscreener: {exc}")
