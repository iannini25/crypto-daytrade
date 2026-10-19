// Dia e semana no horário de Brasília. A semana começa na segunda.
// Desde 2019 o Brasil não tem horário de verão; o fuso entra pelo nome, não por um -3 fixo.

import type { PeriodKey } from './types';

const TZ = 'America/Sao_Paulo';

export interface BrtWall {
  y: number;
  m: number;
  d: number;
  hh: number;
  mm: number;
  ss: number;
  /** 0 = segunda … 6 = domingo. */
  weekday: number;
}

const WEEK: Record<string, number> = { Mon: 0, Tue: 1, Wed: 2, Thu: 3, Fri: 4, Sat: 5, Sun: 6 };

export function brtWall(ms: number): BrtWall {
  const fmt = new Intl.DateTimeFormat('en-US', {
    timeZone: TZ,
    hourCycle: 'h23',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    weekday: 'short',
  });
  const parts = Object.fromEntries(fmt.formatToParts(new Date(ms)).map((p) => [p.type, p.value]));
  let hh = Number(parts.hour);
  if (hh === 24) hh = 0;
  const weekday = WEEK[parts.weekday ?? ''];
  if (weekday === undefined) throw new Error(`dia da semana inesperado: ${parts.weekday}`);
  return {
    y: Number(parts.year),
    m: Number(parts.month),
    d: Number(parts.day),
    hh,
    mm: Number(parts.minute),
    ss: Number(parts.second),
    weekday,
  };
}

/** Meia-noite em Brasília do instante `ms`, em epoch ms. */
export function startOfBrtDay(ms: number): number {
  const w = brtWall(ms);
  const elapsed = ((w.hh * 60 + w.mm) * 60 + w.ss) * 1000 + (ms % 1000);
  return ms - elapsed;
}

export function brtDateString(ms: number): string {
  const w = brtWall(ms);
  const p = (n: number) => String(n).padStart(2, '0');
  return `${w.y}-${p(w.m)}-${p(w.d)}`;
}

/** Início do período, inclusive. `all` começa em 0. */
export function periodStart(nowMs: number, period: PeriodKey): number {
  if (period === 'all') return 0;
  const day = startOfBrtDay(nowMs);
  if (period === 'day') return day;
  return day - brtWall(nowMs).weekday * 86_400_000;
}
