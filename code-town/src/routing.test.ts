import assert from 'node:assert/strict';
import test from 'node:test';
import { helperFromEvent, nameTag, onCryptoDesk } from './agents.ts';
import { AGENTS } from './agents.ts';
import { isErrorEvent, roomFor, type AgentEvent } from './routing.ts';

const chefe = AGENTS.find((a) => a.tag === 'Chefe')!;
const risco = AGENTS.find((a) => a.tag === 'Risco')!;
const noticias = AGENTS.find((a) => a.tag === 'Notícias')!;
const radar = AGENTS.find((a) => a.id === 'radar-x')!;

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

test('scan walks to the chart room', () => {
  assert.equal(roomFor(chefe, ev({ kind: 'scan' })), 'charts');
});

test('noticias goes to the newsroom', () => {
  assert.equal(roomFor(noticias, ev({ kind: 'noticias', agent_id: noticias.id })), 'news');
});

test('macro goes to the newsroom', () => {
  assert.equal(roomFor(chefe, ev({ kind: 'macro' })), 'news');
});

test('whale flow goes on-chain', () => {
  assert.equal(roomFor(chefe, ev({ kind: 'baleia' })), 'whales');
});

test('veto goes to risk', () => {
  assert.equal(roomFor(risco, ev({ kind: 'veto', agent_id: risco.id, status: 'failed' })), 'risk');
});

test('estudo goes to the library', () => {
  assert.equal(roomFor(chefe, ev({ kind: 'estudo' })), 'library');
});

test('group chat goes to the talk table', () => {
  assert.equal(roomFor(chefe, ev({ kind: 'conversa' })), 'talk');
});

test('coding goes to the code room', () => {
  assert.equal(roomFor(chefe, ev({ kind: 'codigo' })), 'code');
});

test('a presentation goes to the projector room', () => {
  assert.equal(roomFor(chefe, ev({ kind: 'apresentacao' })), 'present');
});

test('idle older than 30 min goes to the lounge', () => {
  const old = new Date(Date.now() - 31 * 60 * 1000).toISOString();
  assert.equal(roomFor(chefe, ev({ kind: 'scan', created_at: old })), 'coffee');
});

test('only the crypto desk and its helpers are shown', () => {
  assert.equal(onCryptoDesk(chefe), true);
  assert.equal(onCryptoDesk(AGENTS.find((a) => a.id === 'radar-x')!), true);
  assert.equal(onCryptoDesk(AGENTS.find((a) => a.name === 'Grok Bot')!), false);
  assert.equal(onCryptoDesk(AGENTS.find((a) => a.id === 'leads')!), false);
  assert.equal(onCryptoDesk(helperFromEvent('executor-chefe', 'Executor', 'automação do Chefe')), true);
  assert.equal(onCryptoDesk(helperFromEvent('igor', 'IGORMARCHETTI', 'fila pessoal')), false);
});

test('failed status is an error bubble', () => {
  assert.equal(isErrorEvent(ev({ status: 'failed', kind: 'scan' })), true);
  assert.equal(isErrorEvent(ev({ status: 'ok', kind: 'scan' })), false);
});

test('helpers wear a parent name balloon', () => {
  assert.equal(nameTag(radar), 'Radar X (Notícias)');
  const tmp = helperFromEvent('executor-chefe', 'Executor', 'automação do Chefe');
  assert.equal(tmp.helper, true);
  assert.equal(tmp.temporary, true);
  assert.equal(nameTag(tmp), 'Executor (Chefe)');
});
