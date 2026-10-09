// Fonte "Grok Bot": transforma as linhas de agent_events (Supabase) em snapshots do Habblaud.
// Ocupa o lugar do simulador do ?mock=1 (mesma interface: snapshot() e tick()), então o escritório,
// a vida social, o feed e o "Meu dia" funcionam sem servidor — o site é estático na Vercel.
//
// Cada setor da mesa é uma sala. O agente fica 'working' na sala do último evento por WORK_MS;
// depois fica 'idle' e circula pelo prédio (copa, lounge), como no Habblaud.
import { createClient } from '@supabase/supabase-js';
import type { Activity, ActivityKind, AgentInfo, FeedItem, Notice, OfficeSnapshot, RoomInfo } from '../../../shared/types';
import { hash32 } from '../../../shared/hash';
import { DESK_AGENTS, findAgent, helperFromEvent, nameTag, onCryptoDesk, type AgentConfig } from './agents';
import { activityIcon, isErrorEvent, type AgentEvent } from './routing';
import { agentByTag, deskOf, read } from './interpret';

export interface GrokTickResult {
  changed: boolean;
  feed: FeedItem[];
  notices: Notice[];
}

/** Tempo trabalhando na mesa depois de um evento. */
const WORK_MS = 5 * 60_000;
const RECENT_MAX = 30;

const SECTORS: Array<{ id: string; name: string }> = [
  { id: 'charts', name: 'Painel de Análise' },
  { id: 'talk', name: 'Sala de Reunião · Core' },
  { id: 'news', name: 'Redação · Notícias e Macro' },
  { id: 'library', name: 'Sala de Estudos' },
  { id: 'whales', name: 'On-chain · Baleias' },
  { id: 'stats', name: 'Estatística · Backtests' },
  { id: 'risk', name: 'Risco' },
];
/** Tempo que o agente passa na sala do colega (ou no Core) depois de uma conversa registrada. */
const VISIT_MS = 2 * 60_000;
const TASKS_MAX = 6;

const ROOM_PREFIX = 'grok:';

function kindOf(ev: AgentEvent): ActivityKind {
  const blob = `${ev.kind} ${ev.summary}`.toLowerCase();
  if (isErrorEvent(ev)) return 'error';
  if (/veto|risco|risk/.test(blob)) return 'ask';
  if (/codigo|código|code|script|deploy|commit/.test(blob)) return 'edit';
  if (/convers|reuni|chat|grupo|rotea/.test(blob)) return 'communicate';
  if (/apresent|métrica|metrica|resultado/.test(blob)) return 'respond';
  if (/noticia|notícia|news|headline|macro|radar/.test(blob)) return 'web';
  if (/baleia|whale|on-?chain|fluxo/.test(blob)) return 'search';
  if (/estudo|leitura|paper|livro/.test(blob)) return 'read';
  if (/setup|plano|plan/.test(blob)) return 'plan';
  if (/scan|chart|gr[aá]fico|candle|trade/.test(blob)) return 'read';
  return 'other';
}

function clip(s: string, n: number): string {
  const t = s.replace(/\s+/g, ' ').trim();
  return t.length > n ? `${t.slice(0, n - 1)}…` : t;
}

interface Slot {
  cfg: AgentConfig;
  info: AgentInfo;
  /** Sala da mesa do agente (setor fixo). */
  desk: string;
  /** Visita registrada (conversa com colega ou post no Core): sala e até quando. */
  visit?: { room: string; until: number };
}

export class GrokSource {
  private agents = new Map<string, Slot>();
  private rooms = new Map<string, RoomInfo>();
  private seen = new Set<string>();
  private rev = 0;
  private dirty = true;
  private pendingFeed: FeedItem[] = [];
  private pendingNotices: Notice[] = [];
  private readonly startedAt: number;
  private demoTimer: ReturnType<typeof setInterval> | null = null;
  status = 'conectando ao Supabase…';
  live = false;

  constructor(now = Date.now()) {
    this.startedAt = now;
    SECTORS.forEach((s, i) => {
      const id = ROOM_PREFIX + s.id;
      this.rooms.set(id, { id, name: s.name, path: `mesa/${s.id}`, slot: i, seed: hash32(id), createdAt: now });
    });
    for (const cfg of DESK_AGENTS) this.ensure(cfg, now);
  }

  /** Conecta ao Supabase (ou cai no modo demonstração da mesa). `onData` avisa que chegou evento novo. */
  async start(onData: () => void): Promise<void> {
    const env = import.meta.env as Record<string, string | undefined>;
    const url = env.NEXT_PUBLIC_SUPABASE_URL;
    const key = env.NEXT_PUBLIC_SUPABASE_ANON_KEY;
    if (!url || !key || url.includes('YOUR_PROJECT')) return this.startDemo('sem NEXT_PUBLIC_SUPABASE_* — demonstração', onData);
    try {
      const client = createClient(url, key, { realtime: { params: { eventsPerSecond: 8 } } });
      const { data, error } = await client
        .from('agent_events')
        .select('id,agent_id,agent_name,kind,summary,status,created_at,source_id')
        .order('created_at', { ascending: false })
        .limit(300);
      if (error) throw new Error(error.message);
      for (const row of [...((data ?? []) as AgentEvent[])].reverse()) this.ingest(row, false);
      this.pendingFeed = this.pendingFeed.slice(-120);
      this.live = true;
      this.status = 'ao vivo';
      client
        .channel('habblaud-grok-agent-events')
        .on('postgres_changes', { event: 'INSERT', schema: 'public', table: 'agent_events' }, (payload) => {
          this.ingest(payload.new as AgentEvent, true);
          onData();
        })
        .subscribe((s) => {
          this.status = s === 'SUBSCRIBED' ? 'ao vivo' : s.toLowerCase();
        });
      onData();
    } catch (err) {
      this.startDemo(`Supabase indisponível (${(err as Error).message}) — demonstração`, onData);
    }
  }

  private startDemo(reason: string, onData: () => void): void {
    this.status = reason;
    let tick = 0;
    const now = Date.now();
    DEMO.forEach((d, i) => this.ingest(demoEvent(d, now - (DEMO.length - i) * 45_000, `seed-${i}`), false));
    onData();
    this.demoTimer = setInterval(() => {
      const d = DEMO[tick % DEMO.length];
      this.ingest(demoEvent(d, Date.now(), `live-${tick++}`), true);
      onData();
    }, 7_000);
  }

  stop(): void {
    if (this.demoTimer) clearInterval(this.demoTimer);
  }

  private ensure(cfg: AgentConfig, now: number): Slot {
    let slot = this.agents.get(cfg.id);
    if (slot) return slot;
    const parent = cfg.parent ? (findAgent(cfg.parent) ?? undefined) : undefined;
    const home = deskOf(cfg);
    const seed = hash32(cfg.id);
    const info: AgentInfo = {
      id: cfg.id,
      kind: cfg.helper && parent ? 'sub' : 'main',
      parentId: cfg.helper && parent ? parent.id : undefined,
      roomId: ROOM_PREFIX + home,
      name: nameTag(cfg),
      look: seed % 2 ? 'f' : 'm',
      role: cfg.role,
      title: cfg.role,
      sessionId: cfg.id,
      account: 'grok',
      status: 'idle',
      recent: [],
      tasks: [],
      model: 'Grok Bot',
      startedAt: now,
      lastEventAt: 0,
      statusSince: now,
      stats: { toolCalls: 0, tokensIn: 0, tokensOut: 0, subagents: 0 },
      seed,
    };
    slot = { cfg, info, desk: info.roomId };
    this.agents.set(cfg.id, slot);
    this.dirty = true;
    return slot;
  }

  private resolve(ev: AgentEvent): AgentConfig | null {
    const known = findAgent(ev.agent_id) ?? findAgent(ev.agent_name);
    if (known) return known;
    const label = (ev.agent_name || ev.agent_id || '').trim();
    if (!label) return null;
    const existing = [...this.agents.values()].find((s) => s.cfg.id === ev.agent_id || s.cfg.name.toLowerCase() === label.toLowerCase());
    if (existing) return existing.cfg;
    return helperFromEvent(ev.agent_id || label, ev.agent_name || label, ev.summary || '');
  }

  ingest(ev: AgentEvent, fresh: boolean): void {
    if (!ev?.id || this.seen.has(ev.id)) return;
    this.seen.add(ev.id);
    const cfg = this.resolve(ev);
    if (!cfg || !onCryptoDesk(cfg)) return;
    const at = Date.parse(ev.created_at) || Date.now();
    const slot = this.ensure(cfg, at);
    const info = slot.info;
    const r = read(cfg, ev.kind, ev.summary || '');
    const error = isErrorEvent(ev);
    const peer = r.interaction ? agentByTag(r.interaction.peer) : undefined;
    const peerName = peer ? nameTag(peer) : r.interaction?.peer;
    // Visita só quando o próprio resumo diz que o agente levou algo a alguém (ou postou no Core).
    if (r.corePost) slot.visit = { room: ROOM_PREFIX + 'talk', until: at + VISIT_MS };
    else if (r.interaction?.dir === 'out' && peer) slot.visit = { room: ROOM_PREFIX + deskOf(peer), until: at + VISIT_MS };
    const talk = Boolean(r.interaction) || r.corePost;
    const arrow = r.interaction ? (r.interaction.dir === 'out' ? `→ ${peerName}: ` : `← ${peerName}: `) : r.corePost ? '→ Core: ' : '';
    const act: Activity = {
      id: `ev:${ev.id}`,
      kind: error ? 'error' : r.decision ? 'ask' : talk ? 'communicate' : r.quiet ? 'wait' : kindOf(ev),
      icon: r.decision === 'veto' ? '⛔' : r.decision === 'approve' ? '✅' : talk ? '💬' : r.quiet ? '👀' : activityIcon(ev.kind),
      text: clip(arrow + (ev.summary || ev.kind), 46),
      detail: clip(`${ev.kind} · ${ev.status} — ${ev.summary}`, 300),
      tool: ev.kind,
      at,
      error: error || undefined,
    };
    if (at >= info.lastEventAt) {
      info.activity = act;
      info.lastEventAt = at;
      info.title = clip(ev.summary || cfg.role, 120);
    }
    info.recent = [...info.recent, act].sort((x, y) => x.at - y.at).slice(-RECENT_MAX);
    info.stats.toolCalls++;
    // Tarefas: só as frases do próprio resumo ("Iniciado…", "Na fila…", "… no ar").
    if (r.tasks.length && at >= info.lastEventAt) {
      // tarefa "em andamento" antiga deixa de aparecer quando o agente registra outra (não marcamos como feita:
      // o log não diz isso). Concluídas ficam como histórico.
      info.tasks = info.tasks.filter((x) => x.status === 'completed');
    }
    for (const t of r.tasks) {
      const id = `t:${hash32(t.title)}`;
      info.tasks = [...info.tasks.filter((x) => x.id !== id), { id, title: t.title, status: t.status }];
    }
    info.tasks = info.tasks.slice(-TASKS_MAX);
    if (cfg.helper && cfg.parent) {
      const parent = findAgent(cfg.parent);
      const p = parent && this.agents.get(parent.id);
      if (p && info.recent.length === 1) p.info.stats.subagents++;
    }
    this.place(slot, at);
    const room0 = this.rooms.get(info.roomId)!;
    this.pendingFeed.push({ id: act.id, agentId: info.id, roomId: info.roomId, agentName: info.name, roomName: room0.name, account: 'grok', activity: act });
    if (fresh && (error || r.decision)) {
      const level = r.decision === 'approve' ? 'success' : r.decision === 'veto' || error ? 'alert' : 'info';
      this.pendingNotices.push({ id: `n:${ev.id}`, level, text: `${info.name}: ${clip(ev.summary, 90)}`, agentId: info.id, roomId: info.roomId, at });
    }
    this.dirty = true;
  }

  /** Sala atual: a da visita registrada enquanto durar; senão a mesa do agente. */
  private place(slot: Slot, now: number): void {
    const room = slot.visit && now < slot.visit.until ? slot.visit.room : slot.desk;
    if (slot.visit && now >= slot.visit.until) slot.visit = undefined;
    if (slot.info.roomId !== room) {
      slot.info.roomId = room;
      this.dirty = true;
    }
  }

  tick(now: number): GrokTickResult {
    for (const slot of this.agents.values()) {
      const info = slot.info;
      this.place(slot, now);
      const next = now - info.lastEventAt < WORK_MS ? 'working' : 'idle';
      if (next !== info.status) {
        info.status = next;
        info.statusSince = now;
        this.dirty = true;
      }
    }
    const changed = this.dirty;
    if (changed) this.rev++;
    this.dirty = false;
    const feed = this.pendingFeed;
    const notices = this.pendingNotices;
    this.pendingFeed = [];
    this.pendingNotices = [];
    return { changed, feed, notices };
  }

  snapshot(now = Date.now()): OfficeSnapshot {
    return {
      rev: this.rev,
      serverTime: now,
      rooms: [...this.rooms.values()].map((r) => ({ ...r })),
      agents: [...this.agents.values()].map(({ info }) => ({ ...info, recent: [...info.recent], stats: { ...info.stats } })),
      accounts: [],
      meta: { demo: !this.live, sources: [], startedAt: this.startedAt, version: 'grok' },
    };
  }
}

// ------------------------------------------------------------- demonstração (sem Supabase)

type DemoSpec = { agent: number | string; kind: string; summary: string; status?: string };

const DEMO: DemoSpec[] = [
  { agent: 1, kind: 'scan', summary: 'BTC 15m: range apertando no VWAP' },
  { agent: 2, kind: 'setup', summary: 'Caçando rompimento ETH acima da máxima de ontem' },
  { agent: 3, kind: 'noticias', summary: 'Headline: ETF flow positivo nas últimas 4h' },
  { agent: 4, kind: 'baleia', summary: 'Carteira grande moveu SOL para a exchange' },
  { agent: 5, kind: 'veto', summary: 'Não. Tamanho estoura o limite da mesa.', status: 'failed' },
  { agent: 6, kind: 'apresentacao', summary: 'Métricas de 30d no projetor' },
  { agent: 7, kind: 'estudo', summary: 'Lendo o paper de funding e basis' },
  { agent: 8, kind: 'macro', summary: 'NY abre em alta, DXY caindo' },
  { agent: 0, kind: 'reuniao', summary: 'Reunião: prioridade BTC e ETH hoje' },
  { agent: 'radar-x', kind: 'radar', summary: 'Radar X varreu as manchetes da última hora' },
  { agent: 9, kind: 'roteador', summary: 'Grok Bot distribuiu as tarefas da rodada' },
];

function demoEvent(d: DemoSpec, at: number, id: string): AgentEvent {
  const cfg = typeof d.agent === 'number' ? DESK_AGENTS[d.agent % DESK_AGENTS.length] : (findAgent(d.agent) ?? DESK_AGENTS[0]);
  return {
    id: `demo-${id}`,
    agent_id: cfg.id,
    agent_name: cfg.name,
    kind: d.kind,
    summary: d.summary,
    status: d.status ?? 'ok',
    created_at: new Date(at).toISOString(),
  };
}
