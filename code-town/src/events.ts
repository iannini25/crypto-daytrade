import { createClient, type SupabaseClient } from '@supabase/supabase-js';
import { AGENTS } from './agents';
import type { AgentEvent } from './routing';

export type Mode = 'live' | 'demo';

const url = import.meta.env.NEXT_PUBLIC_SUPABASE_URL as string | undefined;
const key = import.meta.env.NEXT_PUBLIC_SUPABASE_ANON_KEY as string | undefined;

export function supabaseConfigured(): boolean {
  return Boolean(url && key && !url.includes('YOUR_PROJECT'));
}

const SCRIPTS: Array<Pick<AgentEvent, 'agent_id' | 'kind' | 'summary' | 'status'>> = [
  { agent_id: AGENTS[1].id, kind: 'scan', summary: 'BTC 15m: range apertando no VWAP', status: 'ok' },
  { agent_id: AGENTS[2].id, kind: 'setup', summary: 'Caçando rompimento ETH acima da máxima de ontem', status: 'ok' },
  { agent_id: AGENTS[3].id, kind: 'noticias', summary: 'Headline: ETF flow positivo nas últimas 4h', status: 'ok' },
  { agent_id: AGENTS[4].id, kind: 'baleia', summary: 'Carteira grande moveu SOL para a exchange', status: 'ok' },
  { agent_id: AGENTS[5].id, kind: 'veto', summary: 'Não. Tamanho estoura o limite da mesa.', status: 'failed' },
  { agent_id: AGENTS[6].id, kind: 'apresentacao', summary: 'Métricas de 30d no projetor', status: 'ok' },
  { agent_id: AGENTS[7].id, kind: 'estudo', summary: 'Lendo o paper de funding e basis', status: 'ok' },
  { agent_id: AGENTS[8].id, kind: 'macro', summary: 'NY abre em alta, DXY caindo', status: 'ok' },
  { agent_id: AGENTS[9].id, kind: 'conversa', summary: 'Grok Bot abriu a mesa: setup do Caçador', status: 'ok' },
  { agent_id: AGENTS[0].id, kind: 'apresentacao', summary: 'Chefe apresenta o book: prioridade BTC e ETH', status: 'ok' },
  { agent_id: 'radar-x', kind: 'radar', summary: 'Radar X varreu as manchetes da última hora', status: 'ok' },
  { agent_id: 'executor-chefe', kind: 'codigo', summary: 'Executor rodando a automação do Chefe', status: 'ok' },
  { agent_id: 'leads', kind: 'lead', summary: 'Três leads novos no funil da manhã', status: 'ok' },
  { agent_id: 'whatsapp', kind: 'scan', summary: 'Fila do WhatsApp respondida', status: 'ok' },
  { agent_id: 'igormarchetti', kind: 'idle', summary: 'Sem fila. Café.', status: 'ok' },
];

export function seedDemo(now = Date.now()): AgentEvent[] {
  return SCRIPTS.map((s, i) => {
    const agent = AGENTS.find((a) => a.id === s.agent_id);
    const name = agent?.name ?? s.agent_id;
    const stale = s.agent_id === 'igormarchetti';
    const created = new Date(now - (stale ? 45 * 60 * 1000 : i * 40_000)).toISOString();
    return {
      id: `demo-${s.agent_id}`,
      agent_id: s.agent_id,
      agent_name: s.agent_id === 'executor-chefe' ? 'Executor' : name,
      kind: s.kind,
      summary: s.summary,
      status: s.status,
      created_at: created,
    };
  });
}

const EXTRA = [
  { id: AGENTS[1].id, kind: 'scan', summary: 'SOL perdeu a média de 20 no 5m' },
  { id: AGENTS[2].id, kind: 'setup', summary: 'Setup invalidado — stop curto demais' },
  { id: AGENTS[3].id, kind: 'noticias', summary: 'Wire: fala do Fed às 15h BRT' },
  { id: AGENTS[4].id, kind: 'baleia', summary: 'Saída de stable para BTC na whale #12' },
  { id: AGENTS[5].id, kind: 'risco', summary: 'Exposição agregada ainda dentro do teto', status: 'ok' },
  { id: AGENTS[0].id, kind: 'scan', summary: 'Mantém o book. Sem pressa.' },
  { id: AGENTS[8].id, kind: 'macro', summary: 'Londres lateral, Ásia fechou verde' },
  { id: AGENTS[9].id, kind: 'rotear', summary: 'Notícias pediu contexto antes do Chefe' },
  { id: 'whatsapp', kind: 'error', summary: 'Webhook do WhatsApp atrasou', status: 'failed' },
];

export function nextDemo(tick: number, now = Date.now()): AgentEvent {
  const spec = EXTRA[tick % EXTRA.length];
  const agent = AGENTS.find((a) => a.id === spec.id)!;
  return {
    id: `demo-live-${now}-${tick}`,
    agent_id: agent.id,
    agent_name: agent.name,
    kind: spec.kind,
    summary: spec.summary,
    status: spec.status ?? 'ok',
    created_at: new Date(now).toISOString(),
  };
}

export async function startLive(onEvent: (ev: AgentEvent) => void, onStatus: (s: string) => void): Promise<SupabaseClient | null> {
  if (!supabaseConfigured()) return null;
  const client = createClient(url!, key!, { realtime: { params: { eventsPerSecond: 8 } } });
  const { data, error } = await client
    .from('agent_events')
    .select('id,agent_id,agent_name,kind,summary,status,created_at,source_id')
    .order('created_at', { ascending: false })
    .limit(200);
  if (error) {
    onStatus(error.message);
    return null;
  }
  const rows = (data ?? []) as AgentEvent[];
  for (const row of [...rows].reverse()) onEvent(row);
  client
    .channel('code-town-agent-events')
    .on('postgres_changes', { event: 'INSERT', schema: 'public', table: 'agent_events' }, (payload) => {
      onEvent(payload.new as AgentEvent);
    })
    .subscribe((status) => onStatus(status));
  return client;
}
