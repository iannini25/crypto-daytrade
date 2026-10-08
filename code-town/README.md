# Code Town

A live isometric pixel office for the owner's Grok bots. Wall Street trading
floor, crypto tickers, and one avatar per agent. Avatars walk to the room that
matches their latest activity event.

This folder is self-contained. It does not change the trading code elsewhere
in the repo, and it never places orders or holds exchange keys.

Art is procedural canvas pixel art (no paid assets). Camera pan/zoom and the
A* walker are adapted from [Habblaud](https://github.com/marmottajr/habblaud)
(MIT). See `THIRD_PARTY_NOTICES.md`.

## Rooms

A hallway joins the rooms. Each door has a name plate.

| Room | Who ends up there |
| --- | --- |
| Sala de Gráficos | `scan`, charts, setups (Rastreador, Caçador) |
| Redação | `noticias`, `macro`, Radar X |
| On-chain / Baleias | whale and on-chain flow |
| Sala de Risco | `risco`, `veto` (red light when the veto fails) |
| Mesa de conversa | group chat / `conversa` / router |
| Sala de código | `codigo`, automation, scripts |
| Apresentação | `apresentacao`, metrics (Chefe, Estatística) |
| Biblioteca | `estudo` (Estudante) |
| Copa | idle longer than 30 minutes |
| Outros | Leads, Whatsapp, IGORMARCHETTI |

Every avatar has a name balloon. Helpers and unknown sources render smaller, with a badge, as `Nome (Chefe)`. A name that is not in `agents.json` spawns a temporary helper that walks off when it goes idle.

A failed/error status draws a red `!` bubble. Click an avatar for its card.
The right-hand feed lists the latest events with timestamps in `America/Sao_Paulo`.

Add agents by editing `agents.json` (id, name, role, wing, home, colors).

## Run locally (demo, no Supabase)

```bash
cd code-town
npm install
npm test
npm run dev
```

Open http://localhost:5173. Without `NEXT_PUBLIC_SUPABASE_URL` and
`NEXT_PUBLIC_SUPABASE_ANON_KEY` the page runs a mock event generator so the
floor is alive immediately.

Drag to pan, scroll to zoom, or use the room buttons.

## Supabase

1. Create a project.
2. Run `supabase/migrations/20261008000000_agent_events.sql` in the SQL editor.
   It creates `agent_events` (`id`, `agent_id`, `agent_name`, `kind`, `summary`,
   `status`, `created_at`), enables Realtime, and adds an anon **read-only**
   RLS policy. There is no insert policy: writes go through the service role,
   which bypasses RLS.
3. Copy `.env.example` to `.env.local` and fill the URL plus the **anon** key.

```
NEXT_PUBLIC_SUPABASE_URL=https://YOUR_PROJECT.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key
```

Restart `npm run dev`. The badge switches from DEMO to LIVE.

## Vercel

- Framework: Vite
- Root directory: `code-town`
- Build: `npm run build`
- Output: `dist`

Environment variables (Production and Preview):

- `NEXT_PUBLIC_SUPABASE_URL`
- `NEXT_PUBLIC_SUPABASE_ANON_KEY`

Do not put the service role key in Vercel frontend env.

## Pusher (owner's Linux box)

`pusher/push.py` is Python 3, standard library only. It opens the SQLite
activity log, prints the schema it finds, and inserts new rows into
`agent_events`.

```bash
export SUPABASE_URL=https://YOUR_PROJECT.supabase.co
export SUPABASE_SERVICE_ROLE_KEY=your-service-role-key   # not the anon key
export SQLITE_PATH=/workspace/cripto-estudo/mesa/mesa.db # default
python3 code-town/pusher/push.py
```

The CLI that writes the log is `mesa_db log-atividade --agente <name> --tipo <kind> --resumo <text>`.
This repo does not ship that database. On startup the script lists tables and
columns and picks an activity table (`atividade`, `activity`, …) unless you set:

| Env | Meaning |
| --- | --- |
| `ACTIVITY_TABLE` | table name |
| `ACTIVITY_ID_COLUMN` | monotonic id (falls back to `rowid`) |
| `ACTIVITY_AGENT_COLUMN` | agent name (`agente`) |
| `ACTIVITY_KIND_COLUMN` | kind (`tipo`) |
| `ACTIVITY_SUMMARY_COLUMN` | summary (`resumo`) |
| `ACTIVITY_STATUS_COLUMN` | optional |
| `ACTIVITY_TIME_COLUMN` | optional |
| `CURSOR_PATH` | default `code-town/pusher/.cursor.json` |
| `AGENTS_JSON` | default `code-town/agents.json` |

The cursor file stores the last inserted id so rows are not sent twice. It is
gitignored. Names are matched to `agents.json` for `agent_id`.

Run it every 15 seconds:

```bash
while true; do python3 code-town/pusher/push.py; sleep 15; done
```

Never commit `SUPABASE_SERVICE_ROLE_KEY` or `.env.local`.
