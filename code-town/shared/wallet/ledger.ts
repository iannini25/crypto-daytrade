// Custo médio. Comprar realiza a variação do SOL/USDC gasto e põe esse valor de mercado no token.
// Vender realiza o token. Retirar devolve o custo e não é prejuízo. Taxa entra no custo ou no líquido.

import { periodStart } from './periods';
import {
  SOL,
  emptyFigure,
  figure,
  isQuote,
  type Figure,
  type OpenPosition,
  type PeriodFigures,
  type PeriodKey,
  type WalletEvent,
} from './types';

const EPS = 1e-6;

export interface Marks {
  usd(asset: string, qty: number, ts: number): number | null;
  fx(ts: number): number | null;
  currentUsd(asset: string, qty: number): number | null;
  currentFx(): number | null;
  symbol(mint: string): string;
}

interface Lot {
  qty: number;
  costUsd: number;
  costBrl: number;
}

interface Realized {
  ts: number;
  usd: number;
  brl: number;
}

export interface Ledger {
  lots: Map<string, Lot>;
  deposits: { ts: number; usd: number; brl: number }[];
  realized: Realized[];
  error: string | null;
}

export function buildLedger(events: WalletEvent[], marks: Marks): Ledger {
  const lots = new Map<string, Lot>();
  const deposits: Ledger['deposits'] = [];
  const realized: Realized[] = [];
  const bad = events.find((ev) => ev.kind === 'unclassified');
  if (bad && bad.kind === 'unclassified') {
    return { lots, deposits, realized, error: bad.reason };
  }
  for (const ev of events) {
    const error = apply(ev, lots, deposits, realized, marks);
    if (error) return { lots, deposits, realized, error };
  }
  return { lots, deposits, realized, error: null };
}

function lotOf(lots: Map<string, Lot>, asset: string): Lot {
  let lot = lots.get(asset);
  if (!lot) {
    lot = { qty: 0, costUsd: 0, costBrl: 0 };
    lots.set(asset, lot);
  }
  return lot;
}

function take(lots: Map<string, Lot>, asset: string, qty: number): { usd: number; brl: number } | null {
  const lot = lotOf(lots, asset);
  if (qty < -EPS) return null;
  if (lot.qty + 1e-6 < qty) return null;
  const used = Math.min(qty, lot.qty);
  const usd = lot.qty > EPS ? (lot.costUsd / lot.qty) * used : 0;
  const brl = lot.qty > EPS ? (lot.costBrl / lot.qty) * used : 0;
  lot.qty -= used;
  lot.costUsd -= usd;
  lot.costBrl -= brl;
  if (lot.qty <= EPS) {
    lot.qty = 0;
    lot.costUsd = 0;
    lot.costBrl = 0;
  }
  return { usd, brl };
}

function add(lots: Map<string, Lot>, asset: string, qty: number, usd: number, brl: number): void {
  const lot = lotOf(lots, asset);
  lot.qty += qty;
  lot.costUsd += usd;
  lot.costBrl += brl;
}

/** Gasta cotação: realiza a diferença entre o custo e o mercado e devolve o valor de mercado. */
function spendQuote(
  lots: Map<string, Lot>,
  asset: string,
  qty: number,
  ts: number,
  marks: Marks,
  realized: Realized[],
): { usd: number; brl: number } | string {
  const usd = marks.usd(asset, qty, ts);
  const fx = marks.fx(ts);
  if (usd === null || fx === null) return `sem preço de ${asset === SOL ? 'SOL' : 'dólar'} nessa hora`;
  const basis = take(lots, asset, qty);
  if (!basis) return `saiu mais ${asset === SOL ? 'SOL' : 'USDC'} do que tinha entrado`;
  realized.push({ ts, usd: usd - basis.usd, brl: usd * fx - basis.brl });
  return { usd, brl: usd * fx };
}

function apply(ev: WalletEvent, lots: Map<string, Lot>, deposits: Ledger['deposits'], realized: Realized[], marks: Marks): string | null {
  if (ev.kind === 'deposit') {
    const usd = marks.usd(ev.asset, ev.qty, ev.ts);
    const fx = marks.fx(ev.ts);
    if (usd === null || fx === null) return `sem preço na entrada ${ev.sig.slice(0, 8)}`;
    add(lots, ev.asset, ev.qty, usd, usd * fx);
    deposits.push({ ts: ev.ts, usd, brl: usd * fx });
    return null;
  }
  if (ev.kind === 'withdraw') {
    if (!take(lots, ev.asset, ev.qty)) return `retirada maior que o saldo em ${ev.sig.slice(0, 8)}`;
    return null;
  }
  if (ev.kind === 'buy') {
    let costUsd = 0;
    let costBrl = 0;
    for (const leg of ev.spent) {
      const spent = spendQuote(lots, leg.asset, leg.qty, ev.ts, marks, realized);
      if (typeof spent === 'string') return spent;
      costUsd += spent.usd;
      costBrl += spent.brl;
    }
    for (const leg of ev.rebate) {
      const usd = marks.usd(leg.asset, leg.qty, ev.ts);
      const fx = marks.fx(ev.ts);
      if (usd === null || fx === null) return `sem preço do troco em ${ev.sig.slice(0, 8)}`;
      costUsd -= usd;
      costBrl -= usd * fx;
      add(lots, leg.asset, leg.qty, usd, usd * fx);
    }
    if (costUsd < -0.01) return `troco maior que o gasto em ${ev.sig.slice(0, 8)}`;
    add(lots, ev.mint, ev.qty, Math.max(0, costUsd), Math.max(0, costBrl));
    return null;
  }
  if (ev.kind === 'sell') {
    const basis = take(lots, ev.mint, ev.qty);
    if (!basis) return `venda maior que a posição em ${ev.sig.slice(0, 8)}`;
    const fx = marks.fx(ev.ts);
    if (fx === null) return `sem câmbio na venda ${ev.sig.slice(0, 8)}`;
    let proceedsUsd = 0;
    let proceedsBrl = 0;
    for (const leg of ev.got) {
      const usd = marks.usd(leg.asset, leg.qty, ev.ts);
      if (usd === null) return `sem preço do recebido em ${ev.sig.slice(0, 8)}`;
      proceedsUsd += usd;
      proceedsBrl += usd * fx;
      add(lots, leg.asset, leg.qty, usd, usd * fx);
    }
    for (const leg of ev.fees) {
      const spent = spendQuote(lots, leg.asset, leg.qty, ev.ts, marks, realized);
      if (typeof spent === 'string') return spent;
      proceedsUsd -= spent.usd;
      proceedsBrl -= spent.brl;
    }
    realized.push({ ts: ev.ts, usd: proceedsUsd - basis.usd, brl: proceedsBrl - basis.brl });
    return null;
  }
  if (ev.kind === 'convert') {
    const basis = take(lots, ev.spent.asset, ev.spent.qty);
    if (!basis) return `conversão sem saldo em ${ev.sig.slice(0, 8)}`;
    const usd = marks.usd(ev.got.asset, ev.got.qty, ev.ts);
    const fx = marks.fx(ev.ts);
    if (usd === null || fx === null) return `sem preço na conversão ${ev.sig.slice(0, 8)}`;
    realized.push({ ts: ev.ts, usd: usd - basis.usd, brl: usd * fx - basis.brl });
    add(lots, ev.got.asset, ev.got.qty, usd, usd * fx);
    return null;
  }
  return ev.reason;
}

export interface ChainBalances {
  sol: number;
  tokens: { mint: string; qty: number }[];
}

/** Confere o custo médio com o saldo que está na carteira agora. */
export function reconcile(ledger: Ledger, chain: ChainBalances): string | null {
  if (ledger.error) return ledger.error;
  const sol = ledger.lots.get(SOL)?.qty ?? 0;
  if (Math.abs(sol - chain.sol) > 0.00005) {
    return `o SOL calculado (${sol.toFixed(6)}) não fecha com a carteira (${chain.sol.toFixed(6)})`;
  }
  const seen = new Set<string>();
  for (const token of chain.tokens) {
    if (isQuote(token.mint) || token.mint === SOL) continue;
    seen.add(token.mint);
    const qty = ledger.lots.get(token.mint)?.qty ?? 0;
    if (Math.abs(qty - token.qty) > Math.max(0.001, token.qty * 1e-4)) {
      return `o saldo de ${token.mint.slice(0, 4)}… não fecha com a carteira`;
    }
  }
  for (const [asset, lot] of ledger.lots) {
    if (isQuote(asset) || lot.qty <= 0.001) continue;
    if (!seen.has(asset)) return `a carteira não tem mais ${asset.slice(0, 4)}… e o cálculo ainda tem saldo`;
  }
  for (const [asset, lot] of ledger.lots) {
    if (!isQuote(asset) || asset === SOL || lot.qty <= 0.001) continue;
    const chainQty = chain.tokens.find((token) => token.mint === asset)?.qty ?? 0;
    if (Math.abs(lot.qty - chainQty) > 0.001) return `o USDC calculado não fecha com a carteira`;
  }
  return null;
}

function sumDeposits(rows: Ledger['deposits'], from: number): Figure {
  let usd = 0;
  let brl = 0;
  for (const row of rows) {
    if (row.ts < from) continue;
    usd += row.usd;
    brl += row.brl;
  }
  return figure(usd, brl);
}

function splitRealized(rows: Realized[], from: number): { lucro: Figure; prejuizo: Figure } {
  let gainUsd = 0;
  let gainBrl = 0;
  let lossUsd = 0;
  let lossBrl = 0;
  for (const row of rows) {
    if (row.ts < from) continue;
    if (row.usd >= 0) {
      gainUsd += row.usd;
      gainBrl += row.brl;
    } else {
      lossUsd += -row.usd;
      lossBrl += -row.brl;
    }
  }
  return { lucro: figure(gainUsd, gainBrl), prejuizo: figure(lossUsd, lossBrl) };
}

export function openPositions(ledger: Ledger, marks: Marks): OpenPosition[] {
  const out: OpenPosition[] = [];
  for (const [asset, lot] of ledger.lots) {
    if (lot.qty <= 0.0001) continue;
    if (asset !== SOL && isQuote(asset) && lot.qty < 0.01) continue;
    if (asset === SOL && lot.qty < 0.0001) continue;
    const price = asset === SOL ? marks.currentUsd(SOL, 1) : isQuote(asset) ? 1 : marks.currentUsd(asset, 1);
    const fx = marks.currentFx();
    const symbol = asset === SOL ? 'SOL' : isQuote(asset) ? 'USDC' : marks.symbol(asset);
    if (price === null || fx === null) {
      out.push({ mint: asset, symbol, qty: lot.qty, avgUsd: lot.qty ? lot.costUsd / lot.qty : null, priceUsd: null, pnlUsd: null, pnlBrl: null, reason: 'sem preço agora' });
      continue;
    }
    const mark = price * lot.qty;
    out.push({
      mint: asset,
      symbol,
      qty: lot.qty,
      avgUsd: lot.qty ? lot.costUsd / lot.qty : null,
      priceUsd: price,
      pnlUsd: mark - lot.costUsd,
      pnlBrl: mark * fx - lot.costBrl,
    });
  }
  return out.sort((a, b) => Math.abs(b.pnlUsd ?? 0) - Math.abs(a.pnlUsd ?? 0));
}

function abertoOf(positions: OpenPosition[]): Figure {
  if (positions.some((p) => p.pnlUsd === null || p.pnlBrl === null)) {
    const why = positions.find((p) => p.reason)?.reason ?? 'sem preço de uma posição aberta';
    return emptyFigure(why);
  }
  let usd = 0;
  let brl = 0;
  for (const p of positions) {
    usd += p.pnlUsd ?? 0;
    brl += p.pnlBrl ?? 0;
  }
  return figure(usd, brl);
}

const BLANK: PeriodFigures = {
  investido: emptyFigure('ainda não calculado'),
  aportes: emptyFigure('ainda não calculado'),
  prejuizo: emptyFigure('ainda não calculado'),
  lucro: emptyFigure('ainda não calculado'),
  aberto: emptyFigure('ainda não calculado'),
};

export function blankPeriods(reason: string): Record<PeriodKey, PeriodFigures> {
  const fig = emptyFigure(reason);
  const period: PeriodFigures = { investido: fig, aportes: fig, prejuizo: fig, lucro: fig, aberto: fig };
  return { day: period, week: period, all: period };
}

export function figuresFor(ledger: Ledger, marks: Marks, nowMs: number): { periods: Record<PeriodKey, PeriodFigures>; open: OpenPosition[] } {
  if (ledger.error) return { periods: blankPeriods(ledger.error), open: [] };
  const positions = openPositions(ledger, marks);
  const aberto = abertoOf(positions);
  const investido = sumDeposits(ledger.deposits, 0);
  const periods = {} as Record<PeriodKey, PeriodFigures>;
  for (const key of ['day', 'week', 'all'] as const) {
    // Eventos guardam o blockTime em segundos; o período é calculado em ms.
    const from = periodStart(nowMs, key) / 1000;
    const split = splitRealized(ledger.realized, from);
    periods[key] = {
      investido,
      aportes: sumDeposits(ledger.deposits, from),
      prejuizo: split.prejuizo,
      lucro: split.lucro,
      aberto,
    };
  }
  return { periods, open: positions };
}

export { BLANK };
