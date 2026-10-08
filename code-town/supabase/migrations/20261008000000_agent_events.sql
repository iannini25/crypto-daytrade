-- Code Town activity feed.
-- Apply in the Supabase SQL editor or via `supabase db push`.
-- Inserts are service-role only (the pusher). The anon key can SELECT.

create table if not exists public.agent_events (
  id uuid primary key default gen_random_uuid(),
  agent_id text not null,
  agent_name text not null,
  kind text not null,
  summary text not null default '',
  status text not null default 'ok',
  created_at timestamptz not null default now()
);

create index if not exists agent_events_created_at_idx
  on public.agent_events (created_at desc);

create index if not exists agent_events_agent_id_idx
  on public.agent_events (agent_id, created_at desc);

alter table public.agent_events enable row level security;

drop policy if exists "anon read agent_events" on public.agent_events;
create policy "anon read agent_events"
  on public.agent_events
  for select
  to anon, authenticated
  using (true);

-- No INSERT/UPDATE/DELETE policy: the service role bypasses RLS.
-- The anon key cannot write.

do $$
begin
  if not exists (
    select 1 from pg_publication_tables
    where pubname = 'supabase_realtime'
      and schemaname = 'public'
      and tablename = 'agent_events'
  ) then
    alter publication supabase_realtime add table public.agent_events;
  end if;
end $$;
