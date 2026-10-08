#!/usr/bin/env python3
"""Push new mesa activity rows from SQLite into Supabase agent_events.

Reads SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY from the environment.
Never prints those secrets. Column names are guessed from the live schema
and can be overridden with ACTIVITY_* env vars.

Loop example (every 15s):

    while true; do python3 code-town/pusher/push.py; sleep 15; done
"""

from __future__ import annotations

import json
import os
import sqlite3
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = os.environ.get("SQLITE_PATH", "/workspace/cripto-estudo/mesa/mesa.db")
CURSOR_PATH = Path(os.environ.get("CURSOR_PATH", Path(__file__).resolve().parent / ".cursor.json"))
AGENTS_PATH = Path(os.environ.get("AGENTS_JSON", ROOT / "agents.json"))

ID_CANDIDATES = ["id", "rowid"]
AGENT_CANDIDATES = ["agente", "agent", "agent_name", "nome", "name"]
KIND_CANDIDATES = ["tipo", "kind", "type"]
SUMMARY_CANDIDATES = ["resumo", "summary", "texto", "text", "mensagem"]
STATUS_CANDIDATES = ["status", "estado"]
TIME_CANDIDATES = ["created_at", "criado_em", "ts", "timestamp", "created"]


def env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        sys.exit(f"missing {name}")
    return value


def load_agents() -> list[dict]:
    if not AGENTS_PATH.exists():
        return []
    return json.loads(AGENTS_PATH.read_text(encoding="utf-8"))


def match_agent(agents: list[dict], name: str) -> tuple[str, str]:
    q = (name or "").strip().lower()
    for agent in agents:
        label = agent["name"].lower()
        if q == label or q == agent["id"].lower() or q in label or label in q:
            return agent["id"], agent["name"]
    slug = "-".join(q.split()) or "unknown"
    return slug, name or slug


def list_tables(con: sqlite3.Connection) -> list[str]:
    rows = con.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
    ).fetchall()
    return [r[0] for r in rows]


def columns_of(con: sqlite3.Connection, table: str) -> list[str]:
    return [r[1] for r in con.execute(f"PRAGMA table_info({quote_ident(table)})")]


def quote_ident(name: str) -> str:
    if not name.replace("_", "").isalnum():
        raise SystemExit(f"refusing unsafe identifier: {name!r}")
    return '"' + name.replace('"', "") + '"'


def pick(columns: list[str], env_name: str, candidates: list[str], required: bool) -> str | None:
    override = os.environ.get(env_name, "").strip()
    if override:
        if override not in columns and override != "rowid":
            sys.exit(f"{env_name}={override} is not a column of the activity table. Have: {columns}")
        return override
    lower = {c.lower(): c for c in columns}
    for cand in candidates:
        if cand in lower:
            return lower[cand]
    if required:
        sys.exit(
            f"could not find a column for {env_name}. Set it explicitly. Columns: {columns}"
        )
    return None


def choose_table(con: sqlite3.Connection) -> str:
    override = os.environ.get("ACTIVITY_TABLE", "").strip()
    tables = list_tables(con)
    print("sqlite tables:", ", ".join(tables) or "(none)")
    if override:
        if override not in tables:
            sys.exit(f"ACTIVITY_TABLE={override} not in database")
        return override
    for name in ("atividade", "activity", "log_atividade", "atividades", "mesa_atividade"):
        if name in tables:
            return name
    for name in tables:
        cols = [c.lower() for c in columns_of(con, name)]
        if any(c in cols for c in ("agente", "agent")) and any(c in cols for c in ("tipo", "kind", "resumo", "summary")):
            return name
    sys.exit(
        "could not guess the activity table. Set ACTIVITY_TABLE. "
        "Expected something written by `mesa_db log-atividade`."
    )


def load_cursor() -> dict:
    if CURSOR_PATH.exists():
        return json.loads(CURSOR_PATH.read_text(encoding="utf-8"))
    return {}


def save_cursor(data: dict) -> None:
    CURSOR_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = CURSOR_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
    tmp.replace(CURSOR_PATH)


def insert_rows(url: str, key: str, rows: list[dict]) -> None:
    endpoint = url.rstrip("/") + "/rest/v1/agent_events"
    body = json.dumps(rows).encode("utf-8")
    req = urllib.request.Request(
        endpoint,
        data=body,
        method="POST",
        headers={
            "apikey": key,
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "Prefer": "return=minimal",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            if resp.status not in (200, 201, 204):
                sys.exit(f"supabase insert failed: HTTP {resp.status}")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:500]
        sys.exit(f"supabase insert failed: HTTP {exc.code} {detail}")


def main() -> None:
    db_path = DEFAULT_DB
    if not Path(db_path).exists():
        sys.exit(f"sqlite database not found: {db_path} (set SQLITE_PATH)")

    agents = load_agents()

    con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    table = choose_table(con)
    cols = columns_of(con, table)
    print(f"activity table: {table}")
    print("columns:", ", ".join(cols))

    col_id = pick(cols, "ACTIVITY_ID_COLUMN", ID_CANDIDATES, required=False)
    col_agent = pick(cols, "ACTIVITY_AGENT_COLUMN", AGENT_CANDIDATES, required=True)
    col_kind = pick(cols, "ACTIVITY_KIND_COLUMN", KIND_CANDIDATES, required=True)
    col_summary = pick(cols, "ACTIVITY_SUMMARY_COLUMN", SUMMARY_CANDIDATES, required=True)
    col_status = pick(cols, "ACTIVITY_STATUS_COLUMN", STATUS_CANDIDATES, required=False)
    col_time = pick(cols, "ACTIVITY_TIME_COLUMN", TIME_CANDIDATES, required=False)

    use_rowid = col_id is None
    id_expr = "rowid" if use_rowid else quote_ident(col_id)
    cursor = load_cursor()
    last = int(cursor.get("last_id") or 0)
    if cursor.get("table") not in (None, table) or cursor.get("db") not in (None, db_path):
        print("cursor file points at a different table or database; starting from 0")
        last = 0

    select_cols = [
        f"{id_expr} AS _id",
        f"{quote_ident(col_agent)} AS _agent",
        f"{quote_ident(col_kind)} AS _kind",
        f"{quote_ident(col_summary)} AS _summary",
    ]
    if col_status:
        select_cols.append(f"{quote_ident(col_status)} AS _status")
    if col_time:
        select_cols.append(f"{quote_ident(col_time)} AS _time")

    sql = (
        f"SELECT {', '.join(select_cols)} FROM {quote_ident(table)} "
        f"WHERE {id_expr} > ? ORDER BY {id_expr} ASC LIMIT 200"
    )
    print("query cursor last_id =", last)
    url = env("SUPABASE_URL")
    key = env("SUPABASE_SERVICE_ROLE_KEY")
    found = list(con.execute(sql, (last,)))
    print(f"new rows: {len(found)}")
    if not found:
        return

    payload = []
    max_id = last
    for row in found:
        agent_id, agent_name = match_agent(agents, str(row["_agent"] or ""))
        item = {
            "agent_id": agent_id,
            "agent_name": agent_name,
            "kind": str(row["_kind"] or "event"),
            "summary": str(row["_summary"] or ""),
            "status": str(row["_status"]) if col_status and row["_status"] is not None else "ok",
        }
        if col_time and row["_time"]:
            item["created_at"] = str(row["_time"])
        payload.append(item)
        max_id = max(max_id, int(row["_id"]))

    insert_rows(url, key, payload)
    save_cursor({"db": db_path, "table": table, "last_id": max_id})
    print(f"inserted {len(payload)} rows; cursor last_id={max_id}")


if __name__ == "__main__":
    try:
        main()
    except sqlite3.Error as exc:
        sys.exit(f"sqlite error: {exc}")
