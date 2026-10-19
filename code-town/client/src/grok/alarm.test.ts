import assert from 'node:assert/strict';
import test from 'node:test';
import { alarmVisible, applyAlarm, FAKE_ALARM_FLAG, type AlarmState } from './alarm';

const off: AlarmState = { active: false, text: '' };

test('the banner stays hidden when nothing asks for it', () => {
  assert.equal(FAKE_ALARM_FLAG, false);
  assert.equal(alarmVisible(off), false);
  assert.equal(alarmVisible(applyAlarm(off, { kind: 'achado', summary: 'volume subiu', status: 'ok' })), false);
});

test('an agent_events row turns the banner on, and a later clear turns it off', () => {
  const on = applyAlarm(off, { kind: 'fake_alarm', status: 'ok', summary: 'FAKE ALARM — exercício' });
  assert.equal(on.active, true);
  assert.match(on.text, /FAKE ALARM/);
  const cleared = applyAlarm(on, { kind: 'fake_alarm', status: 'off', summary: 'FAKE ALARM' });
  assert.deepEqual(cleared, off);
});

test('the page flag shows the banner without an event', () => {
  assert.equal(alarmVisible(off, false, '?fakeAlarm=1'), true);
  assert.equal(alarmVisible(off, false, '?mock=1'), false);
});
