import assert from 'node:assert/strict';
import test from 'node:test';
import { GrokSource, sectorOf, VISIT_MS, WORK_MS } from './source';
import { findAgent } from './agents';
import type { AgentEvent } from './routing';

const T0 = Date.parse('2026-10-08T13:00:00Z');
let n = 0;
function ev(agent: string, kind: string, summary: string, at: number, extra: Partial<AgentEvent> = {}): AgentEvent {
  const a = findAgent(agent)!;
  return { id: `t${++n}`, agent_id: a.id, agent_name: a.name, kind, summary, status: 'ok', created_at: new Date(at).toISOString(), ...extra };
}
const info = (s: GrokSource, tag: string, now: number) => s.snapshot(now).agents.find((a) => a.id === findAgent(tag)!.id)!;

test('sala livre vira setor', () => {
  assert.equal(sectorOf('Sala de Reunião'), 'talk');
  assert.equal(sectorOf('on-chain'), 'whales');
  assert.equal(sectorOf(''), undefined);
});

test('conversa explícita: os dois se encontram e o balão mostra a mensagem', () => {
  const s = new GrokSource(T0);
  s.ingest(ev('Caçador', 'conversa', 'ETH 1h sem HH, veto mantido', T0, { to_agent: 'Risco' }), true);
  s.tick(T0 + 1000);
  const c = info(s, 'Caçador', T0 + 1000);
  const r = info(s, 'Risco', T0 + 1000);
  assert.equal(c.roomId, 'grok:risk');
  assert.equal(r.roomId, 'grok:risk');
  assert.equal(c.status, 'working');
  assert.equal(r.status, 'working');
  assert.match(c.activity!.text, /^→ Risco: ETH/);
  assert.match(r.activity!.text, /^← Caçador: ETH/);
  s.tick(T0 + VISIT_MS + 1000);
  assert.equal(info(s, 'Caçador', T0 + VISIT_MS + 1000).roomId, 'grok:charts');
});

test('conversa pro Core vai à Sala de Reunião', () => {
  const s = new GrokSource(T0);
  s.ingest(ev('Rastreador', 'conversa', 'BTC D LL confirmado', T0, { to_agent: 'Core' }), true);
  s.tick(T0 + 1000);
  assert.equal(info(s, 'Rastreador', T0 + 1000).roomId, 'grok:talk');
  assert.match(info(s, 'Rastreador', T0 + 1000).activity!.text, /^→ Core:/);
});

test('sem evento por WORK_MS ou com descanso: ocioso', () => {
  const s = new GrokSource(T0);
  s.ingest(ev('Baleias', 'achado', 'ETF BTC fluxo -120M Farside', T0), true);
  s.tick(T0 + 1000);
  assert.equal(info(s, 'Baleias', T0 + 1000).status, 'working');
  s.tick(T0 + WORK_MS + 1000);
  assert.equal(info(s, 'Baleias', T0 + WORK_MS + 1000).status, 'idle');
  s.ingest(ev('Estudante', 'tarefa', 'Lendo Clear cap 16', T0), true);
  s.ingest(ev('Estudante', 'descanso', 'Rodada encerrada', T0 + 5000), true);
  s.tick(T0 + 6000);
  assert.equal(info(s, 'Estudante', T0 + 6000).status, 'idle');
});

test('achado guarda o texto completo no detalhe', () => {
  const s = new GrokSource(T0);
  const long = 'Funding OKX BTC +0,004% e OI subiu 2,1% em 4h; Bybit igual; nenhum sinal de squeeze ainda.';
  s.ingest(ev('Baleias', 'achado', long, T0), true);
  const a = info(s, 'Baleias', T0 + 10).recent.at(-1)!;
  assert.equal(a.tool, 'achado');
  assert.equal(a.detail, long);
});
