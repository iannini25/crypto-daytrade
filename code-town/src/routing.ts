import type { AgentConfig, RoomId } from './agents';

export interface AgentEvent {
  id: string;
  agent_id: string;
  agent_name: string;
  kind: string;
  summary: string;
  status: string;
  created_at: string;
}

const IDLE_MS = 30 * 60 * 1000;

export function isErrorEvent(ev: Pick<AgentEvent, 'kind' | 'status'>): boolean {
  const blob = `${ev.kind} ${ev.status}`.toLowerCase();
  return /error|fail|failed|erro|veto/.test(blob) && /error|fail|failed|erro/.test(blob);
}

/** Room the avatar should walk to for this event. Idle > 30 min overrides to coffee. */
export function roomFor(agent: AgentConfig, ev: AgentEvent | null, now = Date.now()): RoomId {
  if (!ev) return agent.home;
  const age = now - Date.parse(ev.created_at);
  const kind = `${ev.kind} ${ev.summary}`.toLowerCase();
  if (Number.isFinite(age) && age > IDLE_MS && !/error|fail/.test(ev.status.toLowerCase())) {
    return 'coffee';
  }
  if (agent.wing === 'other') return 'other';
  if (/noticia|notícia|news|headline/.test(kind)) return 'news';
  if (/risco|veto|compliance|risk/.test(kind)) return 'risk';
  if (/estudo|study|leitura|biblioteca|research/.test(kind)) return 'library';
  if (/macro|bolsa|forex|world.?clock|câmbio|cambio/.test(kind)) return 'meeting';
  if (/idle|coffee|café|cafe|dorm/.test(kind)) return 'coffee';
  if (/scan|chart|graf|trade|setup|caça|caca|baleia|whale|ticker|book/.test(kind)) return 'trading';
  if (/rotea|route|whiteboard|reuni/.test(kind)) return 'meeting';
  return agent.home;
}

export function poseFor(room: RoomId, ev: AgentEvent | null, moving: boolean): 'walk' | 'sit' | 'sleep' | 'read' | 'talk' {
  if (moving) return 'walk';
  if (!ev) return room === 'coffee' ? 'sleep' : 'sit';
  const age = Date.now() - Date.parse(ev.created_at);
  if (room === 'coffee' && age > IDLE_MS) return 'sleep';
  if (room === 'library') return 'read';
  if (room === 'meeting' || room === 'news') return 'talk';
  if (room === 'coffee') return 'sit';
  return 'sit';
}
