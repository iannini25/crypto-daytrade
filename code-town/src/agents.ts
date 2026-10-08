import raw from '../agents.json' with { type: 'json' };

export type RoomId =
  | 'trading'
  | 'news'
  | 'risk'
  | 'library'
  | 'meeting'
  | 'coffee'
  | 'other';

export interface AgentConfig {
  id: string;
  name: string;
  role: string;
  wing: 'desk' | 'other';
  home: RoomId;
  shirt: string;
  hair: string;
  skin: string;
}

export const AGENTS: AgentConfig[] = raw as AgentConfig[];

export function findAgent(idOrName: string): AgentConfig | undefined {
  const q = idOrName.trim().toLowerCase();
  return AGENTS.find(
    (a) => a.id.toLowerCase() === q || a.name.toLowerCase() === q || a.name.toLowerCase().includes(q) || q.includes(a.name.toLowerCase()),
  );
}
