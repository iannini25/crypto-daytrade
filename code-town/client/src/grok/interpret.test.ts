import assert from 'node:assert/strict';
import test from 'node:test';
import { agentByTag, read } from './interpret';

const ag = (t: string) => agentByTag(t)!;

test('pedido explícito leva o agente até o colega', () => {
  const r = read(ag('Risco'), 'revisao', 'Pedi à Estatística: na bateria 15m Coinbase, saída no stop usa o custo do GATE');
  assert.deepEqual(r.interaction, { peer: 'Estatística', dir: 'out' });
});

test('colega citado antes do verbo não é destino (Macro só leu o Caçador)', () => {
  const r = read(ag('Macro'), 'wake', '19:27 Caçador: GATE Coinbase C proposto, sábado sem trade; nada macro a acrescentar, sem post.');
  assert.equal(r.interaction?.dir, 'in');
  assert.equal(r.quiet, true);
});

test('seta de câmbio BRL->USDC não vira conversa de saída', () => {
  const r = read(ag('Caçador'), 'wake', 'lido: Rastreador confirmou BTC-USDC; custo BRL->USDC sem medida');
  assert.notEqual(r.interaction?.dir, 'out');
});

test('"risco" minúsculo não é o agente Risco', () => {
  const r = read(ag('Estatística'), 'estudo', 'Corrigida a curva da R3_20: 1% de risco dá Sharpe 1,36');
  assert.equal(r.interaction, undefined);
});

test('tarefas saem das frases do próprio resumo', () => {
  const r = read(ag('Estatística'), 'estudo', 'Sombra do swing D no ar (sombra_swing_d.py). Na fila: teste de horário de entrada do swing D.');
  assert.deepEqual(r.tasks.map((t) => t.status), ['completed', 'pending']);
});

test('veto e aprovação viram decisão', () => {
  assert.equal(read(ag('Risco'), 'veto', 'Bateria 15m: nada aprovado').decision, 'veto');
  assert.equal(read(ag('Risco'), 'aprovacao', 'GATE Coinbase do Caçador: aprovado C').decision, 'approve');
});
