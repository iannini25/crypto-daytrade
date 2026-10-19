import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import { buildLedger, figuresFor, reconcile, type Marks } from './ledger';
import { parseWalletTxs, type ChainTx } from './parse';
import { periodStart, startOfBrtDay } from './periods';
import { PUMP_WALLET, SOL, USDC } from './types';

test('o dia e a semana de Brasília começam à meia-noite, a semana na segunda', () => {
  // 19/10/2026 09:04 BRT, uma segunda.
  const monday = Date.parse('2026-10-19T12:04:27Z');
  assert.equal(new Date(startOfBrtDay(monday)).toISOString(), '2026-10-19T03:00:00.000Z');
  assert.equal(periodStart(monday, 'day'), startOfBrtDay(monday));
  assert.equal(periodStart(monday, 'week'), startOfBrtDay(monday));
  assert.equal(periodStart(monday, 'all'), 0);
  // 18/10/2026 23:00 BRT ainda é domingo, semana da segunda anterior.
  const sundayNight = Date.parse('2026-10-19T02:00:00Z');
  assert.equal(new Date(startOfBrtDay(sundayNight)).toISOString(), '2026-10-18T03:00:00.000Z');
  assert.equal(new Date(periodStart(sundayNight, 'week')).toISOString(), '2026-10-12T03:00:00.000Z');
});

function flatMarks(solUsd: number, fx: number): Marks {
  return {
    usd(asset, qty) {
      if (asset === SOL) return solUsd * qty;
      if (asset === USDC) return qty;
      return null;
    },
    fx() {
      return fx;
    },
    currentUsd(asset, qty) {
      if (asset === SOL) return solUsd * qty;
      if (asset === USDC) return qty;
      return null;
    },
    currentFx() {
      return fx;
    },
    symbol() {
      return 'TOK';
    },
  };
}

test('custo médio separa lucro, prejuízo e o que entrou de fora', () => {
  const marks = flatMarks(100, 5);
  const day1 = Date.parse('2026-10-18T15:00:00Z');
  const day2 = Date.parse('2026-10-19T15:00:00Z');
  const events = parseWalletTxs([], PUMP_WALLET).events;
  assert.equal(events.length, 0);
  const priced = flatMarks(100, 5);
  priced.usd = (asset, qty, ts) => {
    const px = ts >= day2 / 1000 + 5 ? 110 : 100;
    if (asset === SOL) return px * qty;
    if (asset === USDC) return qty;
    return null;
  };
  const ledger = buildLedger(
    [
      { kind: 'deposit', ts: day1 / 1000, sig: 'dep1', ord: 0, asset: SOL, qty: 1 },
      { kind: 'deposit', ts: day2 / 1000, sig: 'dep2', ord: 0, asset: SOL, qty: 1 },
      { kind: 'buy', ts: day2 / 1000 + 10, sig: 'buy', ord: 1, mint: 'TOK', qty: 1000, spent: [{ asset: SOL, qty: 0.5 }], rebate: [] },
      { kind: 'sell', ts: day2 / 1000 + 20, sig: 'sell', ord: 2, mint: 'TOK', qty: 1000, got: [{ asset: USDC, qty: 40 }], fees: [] },
    ],
    priced,
  );
  assert.equal(ledger.error, null);
  const now = day2 + 2 * 60 * 60 * 1000;
  const view = figuresFor(ledger, flatMarks(110, 5), now);
  // SOL subiu de 100 para 110 no meio sol gasto: lucro 5. O token custou 55 e vendeu por 40: prejuízo 15.
  assert.ok(Math.abs((view.periods.all.lucro.usd ?? 0) - 5) < 1e-9);
  assert.ok(Math.abs((view.periods.all.prejuizo.usd ?? 0) - 15) < 1e-9);
  assert.ok(Math.abs((view.periods.all.investido.usd ?? 0) - 200) < 1e-9);
  assert.ok(Math.abs((view.periods.day.aportes.usd ?? 0) - 100) < 1e-9);
  assert.ok(Math.abs((view.periods.all.aportes.usd ?? 0) - 200) < 1e-9);
  assert.equal(view.periods.day.investido.usd, view.periods.all.investido.usd);
  assert.equal(view.periods.day.prejuizo.brl, 75);
  const open = view.open.find((p) => p.symbol === 'USDC');
  assert.ok(open);
  assert.ok(Math.abs((open?.qty ?? 0) - 40) < 1e-9);
});

test('o histórico real da carteira fecha depósito, DACITY e saldo', () => {
  const raw = JSON.parse(readFileSync(new URL('./fixtures/wallet-txs.json', import.meta.url), 'utf8')) as ChainTx[];
  const { events, problems } = parseWalletTxs(raw, PUMP_WALLET);
  assert.deepEqual(problems, [], problems.join('\n'));
  assert.equal(events.some((ev) => ev.kind === 'unclassified'), false);
  const deposits = events.filter((ev) => ev.kind === 'deposit');
  const solIn = deposits.filter((ev) => ev.kind === 'deposit' && ev.asset === SOL).reduce((s, ev) => s + (ev.kind === 'deposit' ? ev.qty : 0), 0);
  const usdcIn = deposits.filter((ev) => ev.kind === 'deposit' && ev.asset === USDC).reduce((s, ev) => s + (ev.kind === 'deposit' ? ev.qty : 0), 0);
  assert.ok(Math.abs(solIn - (0.1873 + 0.0494 + 0.097190997)) < 1e-6, `SOL entrou ${solIn}`);
  assert.ok(Math.abs(usdcIn - 12.197126) < 1e-6, `USDC entrou ${usdcIn}`);
  const buys = events.filter((ev) => ev.kind === 'buy' && ev.mint.startsWith('nxPq'));
  const qty = buys.reduce((s, ev) => s + (ev.kind === 'buy' ? ev.qty : 0), 0);
  assert.ok(Math.abs(qty - 5065.016688) < 1e-3, `DACITY ${qty}`);
  const marks: Marks = {
    usd(asset, q) {
      if (asset === SOL) return 104.8 * q;
      if (asset === USDC) return q;
      return null;
    },
    fx() {
      return 5.0453;
    },
    currentUsd(asset, q) {
      if (asset === SOL) return 104.8 * q;
      if (asset === USDC) return q;
      if (asset.startsWith('nxPq')) return 0.006 * q;
      return 0;
    },
    currentFx() {
      return 5.0453;
    },
    symbol(mint) {
      return mint.startsWith('nxPq') ? 'DACITY' : mint.slice(0, 4);
    },
  };
  const ledger = buildLedger(events, marks);
  assert.equal(ledger.error, null, ledger.error ?? '');
  const dacity = ledger.lots.get(buys[0] && buys[0].kind === 'buy' ? buys[0].mint : '')!;
  const avg = dacity.costUsd / dacity.qty;
  assert.ok(avg > 0.004 && avg < 0.009, `preço médio ${avg}`);
  const chainSol = ledger.lots.get(SOL)?.qty ?? 0;
  const chainUsdc = ledger.lots.get(USDC)?.qty ?? 0;
  assert.ok(Math.abs(chainUsdc - 0.3) < 0.001, `USDC ${chainUsdc}`);
  const drift = reconcile(ledger, {
    sol: chainSol,
    tokens: [
      { mint: USDC, qty: chainUsdc },
      { mint: buys[0] && buys[0].kind === 'buy' ? buys[0].mint : '', qty: dacity.qty },
    ],
  });
  assert.equal(drift, null, drift ?? '');
  const view = figuresFor(ledger, marks, Date.parse('2026-10-19T21:00:00Z'));
  // Tudo aconteceu na segunda 19/10/2026 em Brasília: os três filtros coincidem.
  assert.equal(view.periods.day.aportes.usd, view.periods.week.aportes.usd);
  assert.equal(view.periods.week.lucro.usd, view.periods.all.lucro.usd);
  assert.equal(view.periods.all.investido.usd, view.periods.day.investido.usd);
  assert.ok((view.periods.all.aberto.usd ?? 0) !== 0);
});
