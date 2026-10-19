// FAKE ALARM fica escondido até um evento em agent_events ou uma flag explícita.
// A flag de código é false. ?fakeAlarm=1 na URL só serve para ver o banner sem gravar nada.

export interface AlarmState {
  active: boolean;
  text: string;
}

export interface AlarmEvent {
  kind?: string | null;
  status?: string | null;
  summary?: string | null;
}

/** Default off. Do not flip this to show the banner in production. */
export const FAKE_ALARM_FLAG = false;

const OFF = /^(off|clear|hidden|0|false)$/i;

function norm(value: string | null | undefined): string {
  return (value ?? '').trim();
}

/** Latest matching row wins. A row that is not an alarm leaves the previous state alone. */
export function applyAlarm(state: AlarmState, ev: AlarmEvent): AlarmState {
  const kind = norm(ev.kind).toLowerCase();
  const status = norm(ev.status).toLowerCase();
  const summary = norm(ev.summary);
  const marked =
    kind === 'fake_alarm' ||
    kind === 'alarme_falso' ||
    kind === 'fake-alarm' ||
    kind === 'fake_alarm_off' ||
    status === 'fake_alarm' ||
    /\bFAKE ALARM\b/.test(summary);
  if (!marked) return state;
  const off = kind === 'fake_alarm_off' || OFF.test(status) || OFF.test(summary);
  if (off) return { active: false, text: '' };
  return { active: true, text: summary || 'FAKE ALARM' };
}

export function alarmVisible(state: AlarmState, flag = FAKE_ALARM_FLAG, search = ''): boolean {
  if (flag) return true;
  if (/(?:^|[?&])fakeAlarm=1(?:&|$)/.test(search)) return true;
  return state.active;
}
