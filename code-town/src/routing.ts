import type { AgentConfig, RoomId } from './agents';

export interface AgentEvent {
  id: string;
  agent_id: string;
  agent_name: string;
  kind: string;
  summary: string;
  status: string;
  created_at: string;
  source_id?: string | null;
}

const IDLE_MS = 30 * 60 * 1000;

export function isErrorEvent(ev: Pick<AgentEvent, 'kind' | 'status'>): boolean {
  const blob = `${ev.kind} ${ev.status}`.toLowerCase();
  return /error|fail|failed|erro|veto/.test(blob) && /error|fail|failed|erro/.test(blob);
}

export type Pose = 'walk' | 'sit' | 'sleep' | 'read' | 'talk' | 'type' | 'present';

/** Room the avatar should walk to for this event. Idle > 30 min overrides to the lounge. */
export function roomFor(agent: AgentConfig, ev: AgentEvent | null, now = Date.now()): RoomId {
  if (!ev) return agent.home;
  const age = now - Date.parse(ev.created_at);
  const kind = `${ev.kind} ${ev.summary}`.toLowerCase();
  if (Number.isFinite(age) && age > IDLE_MS && !/error|fail/.test(ev.status.toLowerCase())) {
    return 'coffee';
  }
  if (agent.wing === 'other') return 'other';
  if (/codigo|código|code|script|automat|deploy|commit|program/.test(kind)) return 'code';
  if (/convers|grupo|chat|reuni[aã]o|mesa de conversa|\bcore\b/.test(kind)) return 'talk';
  if (/apresent|métrica|metrica|resultado|slide|projetor/.test(kind)) return 'present';
  if (/baleia|whale|on-?chain|fluxo/.test(kind)) return 'whales';
  if (/noticia|notícia|news|headline|macro|bolsa|radar|forex|world.?clock/.test(kind)) return 'news';
  if (/risco|veto|compliance|risk/.test(kind)) return 'risk';
  if (/estudo|study|leitura|biblioteca|research|paper/.test(kind)) return 'library';
  if (/idle|coffee|café|cafe|dorm|copa/.test(kind)) return 'coffee';
  if (/scan|chart|gr[aá]fico|trade|setup|ca[cç]a|ticker|book|candle|vwap/.test(kind)) return 'charts';
  if (/rotea|route|whiteboard/.test(kind)) return 'talk';
  return agent.home;
}

export function poseFor(room: RoomId, ev: AgentEvent | null, moving: boolean): Pose {
  if (moving) return 'walk';
  if (!ev) return room === 'coffee' ? 'sleep' : 'sit';
  const age = Date.now() - Date.parse(ev.created_at);
  if (room === 'coffee' && age > IDLE_MS) return 'sleep';
  if (room === 'library') return 'read';
  if (room === 'talk' || room === 'news') return 'talk';
  if (room === 'code') return 'type';
  if (room === 'present') return 'present';
  if (room === 'charts' || room === 'whales') return 'type';
  if (room === 'coffee') return 'sit';
  return 'sit';
}

export function shouldLeave(agent: AgentConfig, ev: AgentEvent | null, now = Date.now()): boolean {
  if (!agent.temporary || !ev) return false;
  const age = now - Date.parse(ev.created_at);
  const kind = `${ev.kind} ${ev.summary}`.toLowerCase();
  return (Number.isFinite(age) && age > IDLE_MS) || /idle|coffee|café|saiu|encerrou/.test(kind);
}
