// Lê o resumo que cada agente grava (mesa_db log-atividade) e extrai só o que está escrito nele:
// com quem falou (e em que direção), se postou no Core, tarefas iniciadas/na fila/concluídas e decisões.
// Nada aqui inventa movimento: sem menção explícita, o agente fica na própria mesa.
import type { TaskStatus } from '../../../shared/types';
import { AGENTS, type AgentConfig } from './agents';

/** Setor fixo (mesa) de cada agente da mesa, pela tag. */
export const DESK_ROOM: Record<string, string> = {
  Chefe: 'talk',
  'Grok Bot': 'talk',
  Rastreador: 'charts',
  'Caçador': 'charts',
  'Notícias': 'news',
  Macro: 'news',
  'Radar X': 'news',
  Baleias: 'whales',
  Risco: 'risk',
  'Estatística': 'stats',
  Estudante: 'library',
};

export function deskOf(agent: AgentConfig): string {
  const key = agent.tag || agent.name;
  if (DESK_ROOM[key]) return DESK_ROOM[key];
  if (agent.parent && DESK_ROOM[agent.parent]) return DESK_ROOM[agent.parent];
  return 'talk';
}

/** Como cada colega aparece escrito nos resumos (com e sem acento). Sensível a maiúscula: "risco" ≠ "Risco". */
const ALIASES: Array<[RegExp, string]> = [
  [/\bChefe\b/, 'Chefe'],
  [/\bRastreador\b/, 'Rastreador'],
  [/\bCa[cç]ador\b/, 'Caçador'],
  [/\bNot[ií]cias\b/, 'Notícias'],
  [/\bMacro\b/, 'Macro'],
  [/\bBaleias\b/, 'Baleias'],
  [/\bRisco\b/, 'Risco'],
  [/\bEstat[ií]stica\b/, 'Estatística'],
  [/\bEstudante\b/, 'Estudante'],
  [/\bGrok\b/, 'Grok Bot'],
];

/** Verbos de quem ENVIA algo a um colega (o agente vai até ele). */
const OUTGOING = /\b(pedi|propus|enviad[oa]|enviei|informei|levad[oa]|perguntei|sugeri|postei|acordou|avisei|mandei|entreguei)\b/gi;
/** Verbos de quem RECEBE / reage ao que um colega fez (fica na mesa, mas é conversa). */
const INCOMING = /\b(aprovou|aprovad[oa]|aceit[oa]u?|aceitei|corrigiu|confirmou|pediu|registrou|anotou|fechou|decidiu|vetou|recebid[oa]|ordem|lido|li |leitura|propôs|encerrou|adotou|alinhou)\b/i;
/** Postou algo novo no canal do grupo (Core / sala), não só leu. */
const CORE_POST = /\b(Core|canal|reuni[aã]o)\b/;
const QUIET = /\b(sem post|sil[eê]ncio|nada a acrescentar|nada novo|sem mensagem nova|sem adendo|sem pedido|nada p\/|nada pedido|sala fechando|sala encerrando)\b/i;

export interface Interaction {
  /** Tag do colega mencionado (o primeiro que não é o próprio agente). */
  peer: string;
  dir: 'out' | 'in';
}

export interface Reading {
  interaction?: Interaction;
  /** Postou conteúdo no Core (vai à Sala de Reunião). */
  corePost: boolean;
  /** Só leu o canal / nada a fazer. */
  quiet: boolean;
  tasks: Array<{ title: string; status: TaskStatus }>;
  decision?: 'veto' | 'approve' | 'decision';
}

function selfKey(agent: AgentConfig): string {
  return agent.tag || agent.name;
}

export function peersIn(text: string, self: string): string[] {
  const hits: Array<[number, string]> = [];
  for (const [re, tag] of ALIASES) {
    if (tag === self) continue;
    const m = re.exec(text);
    if (m) hits.push([m.index, tag]);
  }
  return hits.sort((a, b) => a[0] - b[0]).map(([, t]) => t);
}

function sentences(text: string): string[] {
  return text
    .split(/(?<=[.;])\s+|\s+·\s+/)
    .map((s) => s.trim())
    .filter(Boolean);
}

const STARTED = /^(?:\d{1,2}[:h]\d{2}[^:]*:\s*)?(iniciad[oa]s?:?|comecei|peguei|montando|refazendo|rodando|estou rodando|em andamento)/i;
const QUEUED = /^(na fila:?|fila:)/i;
const DONE = /\b(no ar|fechad[oa]|conclu[ií]d[oa]|corrigid[oa]s?|criad[oa]|pronto|validad[oa]|encerrad[oa]|refeitos?)\b/i;

export function tasksIn(text: string): Array<{ title: string; status: TaskStatus }> {
  const out: Array<{ title: string; status: TaskStatus }> = [];
  for (const s of sentences(text)) {
    if (QUEUED.test(s)) out.push({ title: s.replace(QUEUED, '').trim(), status: 'pending' });
    else if (STARTED.test(s)) out.push({ title: s, status: 'in_progress' });
    else if (/em andamento/i.test(s)) out.push({ title: s, status: 'in_progress' });
    else if (DONE.test(s) && s.length > 12) out.push({ title: s, status: 'completed' });
  }
  return out.map((t) => ({ ...t, title: t.title.length > 90 ? `${t.title.slice(0, 89)}…` : t.title })).filter((t) => t.title.length > 3);
}

export function read(agent: AgentConfig, kind: string, summary: string): Reading {
  const self = selfKey(agent);
  const text = summary ?? '';
  const quiet = QUIET.test(text);
  const peers = peersIn(text, self);
  // Saída: o colega precisa aparecer DEPOIS do verbo ("Pedi à Estatística", "enviado ... p/ Risco").
  let outPeer: string | undefined;
  let sent = false;
  for (const m of text.matchAll(OUTGOING)) {
    sent = true;
    const after = peersIn(text.slice(m.index! + m[0].length, m.index! + m[0].length + 60), self);
    if (after.length) {
      outPeer = after[0];
      break;
    }
  }
  let interaction: Interaction | undefined;
  if (outPeer) interaction = { peer: outPeer, dir: 'out' };
  else if (peers.length) {
    if (INCOMING.test(text) || /\bwake\b/i.test(kind) || /\bwake\b/i.test(text)) interaction = { peer: peers[0], dir: 'in' };
  }
  const corePost = CORE_POST.test(text) && !quiet && sent;
  const k = kind.toLowerCase();
  const decision = k === 'veto' ? 'veto' : k === 'aprovacao' ? 'approve' : k === 'decisao' ? 'decision' : undefined;
  return { interaction, corePost, quiet, tasks: tasksIn(text), decision };
}

export function agentByTag(tag: string): AgentConfig | undefined {
  return AGENTS.find((a) => (a.tag || a.name) === tag);
}
