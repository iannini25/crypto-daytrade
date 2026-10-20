import assert from 'node:assert/strict';
import test from 'node:test';
import { findAgent, onCryptoDesk } from './agents';
import { deskOf } from './interpret';
import { GrokSource } from './source';
import type { AgentEvent } from './routing';
import type { RoomTheme } from '../art/api';
import { layoutDeskRoom } from '../world/layout/desk-floor';

const T0 = Date.parse('2026-10-20T12:00:00Z');

/** Every desk name the office must count, even when the event id is "unknown". */
const ROSTER: Array<[string, string, string]> = [
  ['Trader - Chefe', 'Trader Crypto - Chefe', 'grok:chefe'],
  ['PumpFun Analista', 'PumpFun Analista', 'grok:pumpfun'],
  ['Monitor X', 'Monitor X', 'grok:monitor-x'],
  ['Monitor Trending', 'Monitor Trending', 'grok:trending'],
  ['Caçador Memecoins', 'Caçador Memecoins', 'grok:cacador'],
  ['Holders e Carteira', 'Holders e Carteira', 'grok:whales'],
  ['Risco Memecoins', 'Risco Memecoins', 'grok:risk'],
  ['Estatística Memecoins', 'Estatística Memecoins', 'grok:stats'],
  ['Estudante Memecoins', 'Estudante Memecoins', 'grok:library'],
  ['Conferência de Dados', 'Conferência de Dados', 'grok:conferencia'],
];

test('cada nome da mesa resolve o agente, a sala e a mesa', () => {
  for (const [name, canonical, room] of ROSTER) {
    const cfg = findAgent(name);
    assert.ok(cfg, name);
    assert.equal(cfg.name, canonical, name);
    assert.equal(onCryptoDesk(cfg), true, name);
    assert.equal(`grok:${deskOf(cfg)}`, room, name);
  }
});

test('Conferência de Dados conta na própria sala mesmo com id unknown ou slug', () => {
  const cfg = findAgent('Conferência de Dados');
  assert.ok(cfg);
  assert.equal(cfg.home, 'conferencia');
  assert.equal(cfg.wing, 'desk');
  assert.equal(findAgent('conferencia-de-dados')?.id, cfg.id);
  assert.equal(findAgent('Conferencia de Dados')?.id, cfg.id);
  assert.equal(findAgent('Macro Bolsas')?.id, cfg.id);
  assert.equal(findAgent('unknown'), undefined);

  const s = new GrokSource(T0);
  const rows: AgentEvent[] = [
    {
      id: 'conf-unknown',
      agent_id: 'unknown',
      agent_name: 'Conferência de Dados',
      kind: 'achado',
      summary: 'os números públicos batem com o painel',
      status: 'ok',
      created_at: new Date(T0).toISOString(),
    },
    {
      id: 'conf-slug',
      agent_id: 'conferencia-de-dados',
      agent_name: 'conferencia-de-dados',
      kind: 'tarefa',
      summary: 'Conferência da rodada registrada',
      status: 'ok',
      created_at: new Date(T0 + 1000).toISOString(),
    },
  ];
  for (const row of rows) s.ingest(row, true);
  s.tick(T0 + 2000);
  const agent = s.snapshot(T0 + 2000).agents.find((a) => a.id === cfg.id)!;
  assert.equal(agent.name, 'Conferência de Dados');
  assert.equal(agent.roomId, 'grok:conferencia');
  assert.equal(agent.stats.toolCalls, 2);
  assert.equal(agent.status, 'working');
  const strangers = s.snapshot(T0 + 2000).agents.filter((a) => a.id === 'unknown' || a.id === 'conferencia-de-dados');
  assert.equal(strangers.length, 0);
});

test('evento com id unknown de cada mesa soma no agente certo', () => {
  const s = new GrokSource(T0);
  ROSTER.forEach(([name], i) => {
    s.ingest(
      {
        id: `desk-${i}`,
        agent_id: 'unknown',
        agent_name: name,
        kind: 'achado',
        summary: 'leitura da mesa',
        status: 'ok',
        created_at: new Date(T0).toISOString(),
      },
      true,
    );
  });
  s.tick(T0 + 10);
  const snap = s.snapshot(T0 + 10);
  for (const [name, canonical, room] of ROSTER) {
    const cfg = findAgent(canonical)!;
    const agent = snap.agents.find((a) => a.id === cfg.id)!;
    assert.equal(agent.name, canonical, name);
    assert.equal(agent.roomId, room, name);
    assert.ok(agent.stats.toolCalls >= 1, name);
  }
});

test('a sala da Conferência tem mesa própria', () => {
  const theme: RoomTheme = {
    carpet: '#2f6b4f',
    carpet2: '#1d4a38',
    wall: { base: '#e7e1d6', trim: '#8d7b62', pattern: 'plain' },
    accent: '#f5c542',
    deskVariant: 'dark',
    chairVariant: 'black',
  };
  const layout = layoutDeskRoom('grok:conferencia', 7, theme);
  assert.ok(layout);
  assert.equal(layout.id, 'grok:conferencia');
  assert.ok(layout.furniture.some((f) => f.kind === 'desk'));
  assert.ok(layout.spots.some((s) => s.kind === 'desk'));
});
