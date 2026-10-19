# Code Town

A live isometric pixel office for the owner's Grok bots. One avatar per agent.
Avatars walk to the room that matches their latest activity event.

This folder is the live dashboard. It reads Supabase `agent_events` and the
public DexScreener API. It never places orders, never signs a transaction, and
never holds a wallet or an API secret. The retired Bybit paper desk lives in
`../legacy/` and is not part of this build.

Art is procedural canvas pixel art (no paid assets). Camera pan/zoom and the
A* walker are adapted from [Habblaud](https://github.com/marmottajr/habblaud)
(MIT). See `THIRD_PARTY_NOTICES.md`.

## Rooms

The Chefe's office sits in the center. Every other desk agent has a room around it, with doors between neighbors. There is no central hallway, reception, restroom, or café. Idle agents sit in the Lounge; a live event sends them to their own room (or to Sala de Reunião · Core when the note is a meeting).

| Room | Who works there |
| --- | --- |
| Trader Crypto - Chefe | the Chefe, at the only desk. One sofa, charts and plants around it |
| PumpFun Analista | pump.fun reads |
| Monitor X | X mentions. Radar X shares this room |
| Monitor Trending | trending Solana / pump.fun |
| Caçador Memecoins | new-mint reads |
| Holders e Carteira | holders and wallet flow |
| Risco Memecoins | `risco`, `veto` |
| Estatística Memecoins | stats |
| Sala de Estudos | Estudante Memecoins |
| Conferência de Dados | public-number checks |
| Sala de Reunião · Core | group chat / `conversa`. Grok Bot works here |
| Lounge | anyone idle |

Names already stored in `agent_events` keep working. `agents.json` lists `aliases` for the previous roster (`PumpFun`, `Notícias`, `Rastreador`, `Caçador`, `Baleias`, `Risco`, `Estatística`, `Estudante`, `Macro Bolsas`). The Chefe stays **Trader Crypto - Chefe**, and **Trader - Chefe** maps to the same agent.

## Read-only market panels

The Mercado button opens two panels fed by the public DexScreener API (no key):

- **$DACITY** (`nxPqZ4F7ux8Vph5NFu25rEP6Kx9Gr1U6Fmj36Rjpump`): price, market cap, liquidity, 24h volume, 24h change.
- **Top 10** Solana pump.fun mints, in the order of `token-boosts/top/v1`, filled from `token-boosts/latest/v1` when needed, with quotes from `tokens/v1`.

There is no buy button. A red **FAKE ALARM** banner stays hidden. It appears only when an `agent_events` row has kind `fake_alarm` (or status `fake_alarm`, or the summary contains `FAKE ALARM`) and the status is not `off`, `clear`, or `hidden`. A later row with status `off` hides it again. Opening the page with `?fakeAlarm=1` shows the banner without writing anything. The code flag `FAKE_ALARM_FLAG` stays `false`.

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
