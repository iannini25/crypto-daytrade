#!/usr/bin/env python3
"""Print a read-only advisory snapshot.

DexScreener for $DACITY and the pump.fun trending list, RugCheck for the
risk summary of one mint (default $DACITY). Nothing is signed or stored.
"""

from __future__ import annotations

import json
import sys

from dexscreener import DACITY_MINT, PublicApiError as DexError, dacity, trending
from rugcheck import PublicApiError as RugError, summary


def collect(mint: str = DACITY_MINT) -> dict:
    dacity_quote = None
    dacity_error = None
    try:
        dacity_quote = dacity()
    except DexError as exc:
        dacity_error = str(exc)
    board = []
    trending_error = None
    try:
        board = trending(10)
    except DexError as exc:
        trending_error = str(exc)
    risk = None
    risk_error = None
    try:
        risk = summary(mint)
    except RugError as exc:
        risk_error = str(exc)
    return {
        "advisory": True,
        "signsTransactions": False,
        "storesKeys": False,
        "dacity": dacity_quote,
        "dacityError": dacity_error,
        "trending": board,
        "trendingError": trending_error,
        "rugcheck": risk,
        "rugcheckError": risk_error,
    }


def main(argv: list[str]) -> int:
    mint = DACITY_MINT
    if "--mint" in argv:
        mint = argv[argv.index("--mint") + 1]
    payload = collect(mint)
    json.dump(payload, sys.stdout, indent=2)
    sys.stdout.write("\n")
    failed = payload["dacityError"] or payload["trendingError"] or payload["rugcheckError"]
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
