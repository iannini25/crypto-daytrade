#!/usr/bin/env python3
"""Read-only RugCheck client.

Public GET of a token report. No API key, no wallet, no transaction.
The default printout is a short risk summary, not the raw holder graph.
"""

from __future__ import annotations

import json
import sys
import urllib.request

API = "https://api.rugcheck.xyz"
USER_AGENT = "iannini-memecoin-desk/1.0 (advisory; read-only)"


class PublicApiError(RuntimeError):
    pass


def get_json(url: str):
    if not url.startswith(API + "/"):
        raise PublicApiError(f"refusing non-RugCheck URL: {url}")
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


def risk_names(risks) -> list[str]:
    names: list[str] = []
    for risk in risks or []:
        if isinstance(risk, str) and risk.strip():
            names.append(risk.strip())
        elif isinstance(risk, dict):
            label = risk.get("name") or risk.get("description") or risk.get("level")
            if label:
                names.append(str(label))
    return names[:12]


def summarize(report: dict, mint: str) -> dict:
    risks = report.get("risks") or []
    return {
        "mint": report.get("mint") or mint,
        "score": report.get("score"),
        "score_normalised": report.get("score_normalised"),
        "rugged": report.get("rugged"),
        "lpLockedPct": report.get("lpLockedPct"),
        "totalHolders": report.get("totalHolders"),
        "freezeAuthority": report.get("freezeAuthority"),
        "mintAuthority": report.get("mintAuthority"),
        "launchpad": report.get("launchpad"),
        "risks": risk_names(risks),
        "source": f"{API}/v1/tokens/{mint}/report",
    }


def report(mint: str) -> dict:
    return get_json(f"{API}/v1/tokens/{mint}/report")


def summary(mint: str) -> dict:
    return summarize(report(mint), mint)


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("usage: rugcheck.py <mint> [--raw]", file=sys.stderr)
        return 2
    mint = argv[1]
    raw = "--raw" in argv[2:]
    payload = report(mint) if raw else summary(mint)
    json.dump(payload, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv))
    except PublicApiError as exc:
        sys.exit(f"rugcheck: {exc}")
