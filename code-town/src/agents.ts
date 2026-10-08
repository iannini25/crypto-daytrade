import raw from '../agents.json' with { type: 'json' };

export type RoomId =
  | 'charts'
  | 'news'
  | 'whales'
  | 'risk'
  | 'talk'
  | 'code'
  | 'present'
  | 'library'
  | 'coffee'
  | 'other';

export interface AgentConfig {
  id: string;
  name: string;
  /** Short label drawn in the name balloon. */
  tag?: string;
  role: string;
  wing: 'desk' | 'other';
  home: RoomId;
  shirt: string;
  hair: string;
  skin: string;
  /** Smaller outfit and a badge. Routines and executors. */
  helper?: boolean;
  /** Main agent this helper works for. */
  parent?: string;
  /** Spawned from an event; leaves the floor when idle. */
  temporary?: boolean;
}

export const AGENTS: AgentConfig[] = raw as AgentConfig[];

export function nameTag(agent: AgentConfig): string {
  const base = agent.tag || agent.name;
  if (agent.helper && agent.parent) return `${base} (${agent.parent})`;
  return base;
}

export function findAgent(idOrName: string): AgentConfig | undefined {
  const q = idOrName.trim().toLowerCase();
  if (!q) return undefined;
  return AGENTS.find((a) => {
    const tag = (a.tag || '').toLowerCase();
    return a.id.toLowerCase() === q || a.name.toLowerCase() === q || tag === q;
  });
}

export function guessParent(text: string): string | undefined {
  const q = text.toLowerCase();
  for (const agent of AGENTS) {
    if (agent.helper) continue;
    const tag = (agent.tag || agent.name).toLowerCase();
    if (tag && q.includes(tag)) return agent.tag || agent.name;
  }
  return undefined;
}

const SHIRTS = ['#e8d5a3', '#8fd3c8', '#f0a070', '#b9a0e8', '#f2f2f2'];
const HAIR = ['#1a1a1a', '#5a3a1a', '#c8c8c8', '#3b2414'];
const SKIN = ['#f1c27d', '#e0ac69', '#c68642', '#8d5524', '#ffdbac'];

export function helperFromEvent(agentId: string, agentName: string, summary: string): AgentConfig {
  const parent = guessParent(`${agentName} ${summary}`);
  const key = `${agentId}:${agentName}`;
  let n = 0;
  for (const ch of key) n = (n * 33 + ch.charCodeAt(0)) >>> 0;
  return {
    id: agentId || `tmp-${n.toString(16)}`,
    name: agentName || 'Ajudante',
    tag: agentName || 'Ajudante',
    role: parent ? `Ajudante de ${parent}` : 'Ajudante temporário',
    wing: 'desk',
    home: 'coffee',
    shirt: SHIRTS[n % SHIRTS.length],
    hair: HAIR[n % HAIR.length],
    skin: SKIN[n % SKIN.length],
    helper: true,
    parent,
    temporary: true,
  };
}
