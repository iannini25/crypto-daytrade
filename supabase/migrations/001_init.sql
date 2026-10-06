-- Mesa de paper trading (Bernardo Iannini).
-- Simulação. Nenhuma ordem real. Sem segredo, sem chave de API, sem service_role.
--
-- RLS fica ligado e sem policy: anon não recebe GRANT, então a chave anônima
-- não lê nada até você decidir o contrário. Os blocos de policy estão comentados
-- de propósito. Não use auth.jwt() -> user_metadata (o usuário edita esse campo).

create table public.signals (
  id uuid primary key default gen_random_uuid(),
  created_at timestamptz not null default now(),
  symbol text not null check (symbol in ('BTCUSDT', 'ETHUSDT', 'SOLUSDT')),
  side text not null check (side in ('buy', 'sell', 'none')),
  regime_alta boolean,
  close_price numeric,
  sma100 numeric,
  atr14 numeric,
  stop_price numeric,
  reason text,
  blocked boolean not null default false,
  block_reason text,
  source text not null default 'run_signal.py',
  raw jsonb
);

create table public.paper_trades (
  id text primary key,
  symbol text not null check (symbol in ('BTCUSDT', 'ETHUSDT', 'SOLUSDT')),
  status text not null default 'open' check (status in ('open', 'closed')),
  opened_at timestamptz,
  closed_at timestamptz,
  entry_price numeric,
  stop_price numeric,
  exit_price numeric,
  qty numeric,
  notional_usdt numeric,
  fees_usdt numeric,
  pnl_usdt numeric,
  pnl_brl numeric,
  r_multiple numeric,
  exit_reason text,
  entry_reason text
);

create table public.equity_snapshots (
  id uuid primary key default gen_random_uuid(),
  ts timestamptz not null default now(),
  equity_usdt numeric not null,
  equity_brl numeric,
  usdtbrl numeric,
  cash_usdt numeric,
  positions_usdt numeric,
  pnl_since_start_pct numeric,
  kill_switch boolean not null default false
);

create table public.agent_notes (
  id uuid primary key default gen_random_uuid(),
  created_at timestamptz not null default now(),
  agent text not null check (agent in ('chefe', 'rastreador', 'cacador', 'noticias', 'baleias', 'risco')),
  symbol text check (symbol is null or symbol in ('BTCUSDT', 'ETHUSDT', 'SOLUSDT')),
  stance text not null default 'info' check (stance in ('info', 'proposta', 'rejeitado')),
  body text not null,
  discarded boolean not null default false
);

create table public.macro_calendar (
  event_date date primary key,
  name text not null,
  blocks_entries boolean not null default true,
  notes text
);

comment on table public.signals is 'Sinais do paper. SMA100 diária. Sem ordem real.';
comment on table public.paper_trades is 'Trades simulados. id no formato P0001.';
comment on table public.equity_snapshots is 'Patrimônio da conta simulada, em USDT para o kill switch.';
comment on table public.agent_notes is 'Notas dos bots. Rejeição do Risco deve ser descartada pelo chefe.';
comment on table public.macro_calendar is 'Dias sem entrada nova: CPI, FOMC, payroll, PCE.';

create index signals_created_at_idx on public.signals (created_at desc);
create index signals_symbol_idx on public.signals (symbol, created_at desc);
create index paper_trades_opened_at_idx on public.paper_trades (opened_at desc);
create index paper_trades_open_idx on public.paper_trades (symbol) where status = 'open';
create index equity_snapshots_ts_idx on public.equity_snapshots (ts desc);
create index agent_notes_created_at_idx on public.agent_notes (created_at desc);

-- Calendário já usado em trading-system/config.py (EVENTOS_BLOQUEIO), outubro/novembro 2026.
insert into public.macro_calendar (event_date, name, blocks_entries, notes) values
  ('2026-10-14', 'CPI EUA 09:30 BRT', true, 'Sem entrada nova. Horário de verão dos EUA ainda vale.'),
  ('2026-10-28', 'FOMC 15:00 BRT (coletiva 15:30)', true, 'Sem entrada nova.'),
  ('2026-10-29', 'PIB 3T + PCE 09:30 BRT', true, 'Sem entrada nova.'),
  ('2026-11-06', 'Payroll 10:30 BRT', true, 'Depois do fim do horário de verão nos EUA, o dado cai dentro da janela.'),
  ('2026-11-10', 'CPI EUA 10:30 BRT', true, 'Dentro da janela 10:00–12:30 BRT.');

alter table public.signals enable row level security;
alter table public.paper_trades enable row level security;
alter table public.equity_snapshots enable row level security;
alter table public.agent_notes enable row level security;
alter table public.macro_calendar enable row level security;

revoke all on table public.signals from public, anon;
revoke all on table public.paper_trades from public, anon;
revoke all on table public.equity_snapshots from public, anon;
revoke all on table public.agent_notes from public, anon;
revoke all on table public.macro_calendar from public, anon;

-- authenticated ainda não vê linha nenhuma: não há policy.
-- service_role ignora RLS na Supabase. Não coloque essa chave no Next.js.
grant select, insert, update, delete on table public.signals to authenticated, service_role;
grant select, insert, update, delete on table public.paper_trades to authenticated, service_role;
grant select, insert, update, delete on table public.equity_snapshots to authenticated, service_role;
grant select, insert, update, delete on table public.agent_notes to authenticated, service_role;
grant select, insert, update, delete on table public.macro_calendar to authenticated, service_role;

-- Depois de criar um usuário no Auth, descomente UMA policy por tabela e troque
-- auth.uid() se um dia a mesa tiver mais de uma pessoa. Não use user_metadata.
-- Login anônimo também cai em `authenticated`: não ligue esse provedor aqui.
--
-- create policy desk_rw on public.signals
--   for all to authenticated
--   using ((select auth.uid()) is not null)
--   with check ((select auth.uid()) is not null);
-- create policy desk_rw on public.paper_trades
--   for all to authenticated
--   using ((select auth.uid()) is not null)
--   with check ((select auth.uid()) is not null);
-- create policy desk_rw on public.equity_snapshots
--   for all to authenticated
--   using ((select auth.uid()) is not null)
--   with check ((select auth.uid()) is not null);
-- create policy desk_rw on public.agent_notes
--   for all to authenticated
--   using ((select auth.uid()) is not null)
--   with check ((select auth.uid()) is not null);
-- create policy desk_rw on public.macro_calendar
--   for all to authenticated
--   using ((select auth.uid()) is not null)
--   with check ((select auth.uid()) is not null);
