#!/usr/bin/env python3
"""Activity log for the memecoin desk.

The agent list is code-town/agents.json — the same file the office uses.
There is no second roster. Matching ignores accents and hyphens.

    python3 code-town/mesa_db.py log-atividade --agente "Monitor X" --tipo achado --resumo "..."
    python3 code-town/mesa_db.py ociosos
    python3 code-town/mesa_db.py agentes

This script runs on the box. A Vercel deploy does not update it. The checkout
at /workspace has to git pull. If `mesa_db` on PATH is the older program under
/workspace/cripto-estudo, that tree is separate: call this file.
"""

from __future__ import annotations

import argparse
import os
import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "pusher"))
from push import find_agent, load_agents  # noqa: E402

# The ten desk agents. Grok Bot routes; Radar X is a helper of Monitor X.
DESK_NAMES = (
    "Trader Crypto - Chefe",
    "PumpFun Analista",
    "Monitor X",
    "Monitor Trending",
    "Caçador Memecoins",
    "Holders e Carteira",
    "Risco Memecoins",
    "Estatística Memecoins",
    "Estudante Memecoins",
    "Conferência de Dados",
)

IDLE_MINUTES = 20
TABLE = "atividade"


def db_path() -> Path:
    raw = os.environ.get("SQLITE_PATH", "").strip()
    if raw:
        return Path(raw)
    return ROOT / "mesa" / "mesa.db"


def desk_roster(agents: list[dict]) -> list[dict]:
    by_name = {a.get("name"): a for a in agents}
    missing = [name for name in DESK_NAMES if name not in by_name]
    if missing:
        raise SystemExit("agents.json is missing: " + ", ".join(missing))
    return [by_name[name] for name in DESK_NAMES]


def connect(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(path)
    con.row_factory = sqlite3.Row
    con.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {TABLE} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            agente TEXT NOT NULL,
            tipo TEXT NOT NULL,
            resumo TEXT NOT NULL,
            status TEXT,
            created_at TEXT NOT NULL
        )
        """
    )
    con.commit()
    return con


def log_atividade(agente: str, tipo: str, resumo: str, status: str) -> int:
    agents = load_agents()
    found = find_agent(agents, agente)
    if not found:
        names = "\n".join(f"  {name}" for name in DESK_NAMES)
        print(f'"{agente}" não está na lista de agentes.\nPasse um destes nomes:\n{names}', file=sys.stderr)
        return 2
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    con = connect(db_path())
    cur = con.execute(
        f"INSERT INTO {TABLE} (agente, tipo, resumo, status, created_at) VALUES (?, ?, ?, ?, ?)",
        (found["name"], tipo, resumo, status, now),
    )
    con.commit()
    print(f"ok {found['name']} id={cur.lastrowid}")
    return 0


def _parse_time(value: str | None) -> datetime | None:
    if not value:
        return None
    text = value.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def latest_by_agent(con: sqlite3.Connection) -> dict[str, sqlite3.Row]:
    rows = con.execute(
        f"SELECT agente, tipo, resumo, created_at FROM {TABLE} ORDER BY id ASC"
    ).fetchall()
    latest: dict[str, sqlite3.Row] = {}
    agents = load_agents()
    for row in rows:
        found = find_agent(agents, row["agente"] or "")
        key = found["name"] if found else row["agente"]
        latest[key] = row
    return latest


def ociosos(now: datetime | None = None, minutes: int = IDLE_MINUTES) -> int:
    now = now or datetime.now(timezone.utc)
    roster = desk_roster(load_agents())
    con = connect(db_path())
    latest = latest_by_agent(con)
    limit = timedelta(minutes=minutes)
    idle: list[str] = []
    lines: list[str] = []
    for agent in roster:
        name = agent["name"]
        row = latest.get(name)
        if row is None:
            idle.append(name)
            lines.append(f"{name} — ocioso — sem registro")
            continue
        at = _parse_time(row["created_at"])
        kind = (row["tipo"] or "").strip().lower()
        stale = at is None or now - at >= limit
        if kind == "descanso" or stale:
            idle.append(name)
            when = row["created_at"] or "sem horário"
            lines.append(f"{name} — ocioso — {kind or 'atividade'} {when}")
        else:
            lines.append(f"{name} — trabalhando — {kind} {row['created_at']}")
    print(f"ociosos {len(idle)}/{len(roster)}")
    print("\n".join(lines))
    return 0


def agentes() -> int:
    roster = desk_roster(load_agents())
    print("nome que o agente deve passar em --agente")
    for agent in roster:
        aliases = agent.get("aliases") or []
        extra = f"  (também aceita: {', '.join(aliases)})" if aliases else ""
        print(f"  {agent['name']}{extra}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="mesa_db", description="Log da mesa. A lista é code-town/agents.json.")
    sub = parser.add_subparsers(dest="command", required=True)

    log = sub.add_parser("log-atividade", help="Grava uma linha de atividade")
    log.add_argument("--agente", required=True)
    log.add_argument("--tipo", required=True)
    log.add_argument("--resumo", required=True)
    log.add_argument("--status", default="ok")

    idle = sub.add_parser("ociosos", help="Lista os 10 agentes da mesa e quem está parado")
    idle.add_argument("--minutes", type=int, default=IDLE_MINUTES)

    sub.add_parser("agentes", help="Imprime o nome exato de cada agente")

    args = parser.parse_args(argv)
    if args.command == "log-atividade":
        return log_atividade(args.agente, args.tipo, args.resumo, args.status)
    if args.command == "ociosos":
        return ociosos(minutes=args.minutes)
    if args.command == "agentes":
        return agentes()
    print(f"comando desconhecido {args.command}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
