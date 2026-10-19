import assert from 'node:assert/strict';
import test from 'node:test';
import { mulberry32 } from '../../../../shared/hash';
import { CHEFE_OFFICE_REST, isChefeAgent, rollChefeRest } from './behavior';

test('o Chefe ocioso sorteia o próprio sofá na maior parte das vezes', () => {
  assert.equal(isChefeAgent({ name: 'Trader Crypto - Chefe' }), true);
  assert.equal(isChefeAgent({ name: 'Trader - Chefe' }), true);
  assert.equal(isChefeAgent({ name: 'Caçador Memecoins' }), false);
  assert.equal(rollChefeRest(() => 0), 'office');
  assert.equal(rollChefeRest(() => CHEFE_OFFICE_REST - 0.0001), 'office');
  assert.equal(rollChefeRest(() => CHEFE_OFFICE_REST), 'lounge');
  let office = 0;
  const rng = mulberry32(7);
  for (let i = 0; i < 1000; i++) if (rollChefeRest(rng) === 'office') office++;
  assert.ok(office > 850 && office < 950, String(office));
});
