-- Aditivo: destinatário de conversa e sala informada pelo agente (dashboard ao vivo da mesa).
-- Linhas antigas ficam com NULL. Aplicado em produção em 2026-10-08 (migration agent_events_to_agent_room).
alter table public.agent_events add column if not exists to_agent text, add column if not exists room text;
-- push_agent_events (token-checked, SECURITY DEFINER) passou a aceitar e->>'to_agent' (≤64) e e->>'room' (≤40).
