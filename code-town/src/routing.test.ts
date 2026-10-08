import assert from 'node:assert/strict';
import test from 'node:test';
import { AGENTS } from './agents.ts';
import { isErrorEvent, roomFor, type AgentEvent } from './routing.ts';

const chefe = AGENTS[0];
const risco = AGENTS.find((a) => a.name === 'Risco')!;
const noticias = AGENTS.find((a) => a.name === 'Notícias')!;

function ev(partial: Partial<AgentEvent>): AgentEvent {
  return {
    id: '1',
    agent_id: chefe.id,
    agent_name: chefe.name,
    kind: 'scan',
    summary: 'olhando o book',
    status: 'ok',
    created_at: new Date().toISOString(),
    ...partial,
  };
}

test('scan walks to the trading floor', () => {
  assert.equal(roomFor(chefe, ev({ kind: 'scan' })), 'trading');
});

test('noticias goes to the news room', () => {
  assert.equal(roomFor(noticias, ev({ kind: 'noticias', agent_id: noticias.id })), 'news');
});

test('veto goes to risk', () => {
  assert.equal(roomFor(risco, ev({ kind: 'veto', agent_id: risco.id, status: 'failed' })), 'risk');
});

test('estudo goes to the library', () => {
  assert.equal(roomFor(chefe, ev({ kind: 'estudo' })), 'library');
});

test('macro goes to the meeting room (world clocks)', () => {
  assert.equal(roomFor(chefe, ev({ kind: 'macro' })), 'meeting');
});

test('idle older than 30 min goes to coffee', () => {
  const old = new Date(Date.now() - 31 * 60 * 1000).toISOString();
  assert.equal(roomFor(chefe, ev({ kind: 'scan', created_at: old })), 'coffee');
});

test('other-wing bots stay in the other business wing', () => {
  const leads = AGENTS.find((a) => a.id === 'leads')!;
  assert.equal(roomFor(leads, ev({ kind: 'scan', agent_id: leads.id })), 'other');
});

test('failed status is an error bubble', () => {
  assert.equal(isErrorEvent(ev({ status: 'failed', kind: 'scan' })), true);
  assert.equal(isErrorEvent(ev({ status: 'ok', kind: 'scan' })), false);
});
