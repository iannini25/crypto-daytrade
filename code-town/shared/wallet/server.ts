// Busca o histórico público da carteira, o preço do SOL, o câmbio e a cotação atual.
// Cache de dois minutos. Sem chave, sem assinatura.

import { buildLedger, figuresFor, reconcile, type ChainBalances, type Marks } from './ledger';
import { parseWalletTxs, type ChainTx } from './parse';
import { brtDateString } from './periods';
import { PUMP_WALLET, SOL, USDC, USDT, WSOL_MINT, type WalletPnl } from './types';

const RPCS = ['https://api.mainnet-beta.solana.com', 'https://solana-rpc.publicnode.com'];
const TOKEN = 'TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA';
const TOKEN_2022 = 'TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb';
const TTL_MS = 120_000;
const UA = 'iannini-wallet-pnl/1.0';

interface Cache {
  at: number;
  body: WalletPnl;
}

let cache: Cache | null = null;
let inflight: Promise<WalletPnl> | null = null;

export async function handleWalletPnl(nowMs = Date.now()): Promise<Response> {
  try {
    const body = await load(nowMs);
    return Response.json(body, {
      headers: { 'cache-control': 'public, max-age=60, s-maxage=120, stale-while-revalidate=60' },
    });
  } catch (error) {
    const reason = error instanceof Error ? error.message : 'falha ao ler a carteira';
    const body: WalletPnl = {
      ok: false,
      wallet: PUMP_WALLET,
      computedAt: nowMs,
      solUsd: null,
      fxBrl: null,
      note: reason,
      periods: {
        day: blank(reason),
        week: blank(reason),
        all: blank(reason),
      },
      open: [],
      sources: 'RPC Solana, CoinGecko, Frankfurter, DexScreener',
    };
    return Response.json(body, { headers: { 'cache-control': 'no-store' } });
  }
}

function blank(reason: string) {
  const fig = { usd: null, brl: null, reason };
  return { investido: fig, aportes: fig, prejuizo: fig, lucro: fig, aberto: fig };
}

async function load(nowMs: number): Promise<WalletPnl> {
  if (cache && nowMs - cache.at < TTL_MS) return cache.body;
  if (!inflight) {
    inflight = compute(nowMs)
      .then((body) => {
        if (body.ok) cache = { at: Date.now(), body };
        return body;
      })
      .finally(() => {
        inflight = null;
      });
  }
  return inflight;
}

async function compute(nowMs: number): Promise<WalletPnl> {
  const [txs, balances] = await Promise.all([fetchHistory(PUMP_WALLET), fetchBalances(PUMP_WALLET)]);
  const { events, problems } = parseWalletTxs(txs, PUMP_WALLET);
  if (!txs.length) throw new Error('a carteira não tem transações visíveis no RPC público');
  const times = txs.map((tx) => tx.blockTime).filter((t): t is number => typeof t === 'number');
  const from = Math.min(...times) - 3600;
  const to = Math.max(nowMs / 1000, Math.max(...times)) + 60;
  const [solPoints, fxSeries, fxNow, quotes] = await Promise.all([
    fetchSolUsd(from, to),
    fetchFxSeries(Math.min(...times) * 1000, nowMs),
    fetchFxNow(),
    fetchQuotes(balances),
  ]);
  const marks = makeMarks(solPoints, fxSeries, fxNow, quotes);
  const ledger = buildLedger(events, marks);
  const chain: ChainBalances = { sol: balances.sol, tokens: balances.tokens };
  const drift = reconcile(ledger, chain);
  const problem = problems[0] ?? ledger.error ?? drift;
  const built = problem ? null : figuresFor(ledger, marks, nowMs);
  const note = problem
    ? problem
    : 'Custo médio por token, taxas incluídas. Investido é tudo que entrou de fora, no câmbio da hora. Aportes, prejuízo e lucro seguem o filtro em Brasília (semana começa na segunda). Em aberto é a marcação de agora e não muda com o filtro. Retirada de SOL/USDC não é prejuízo.';
  const periods = built?.periods ?? {
    day: blank(problem ?? 'sem dados'),
    week: blank(problem ?? 'sem dados'),
    all: blank(problem ?? 'sem dados'),
  };
  return {
    ok: !problem,
    wallet: PUMP_WALLET,
    computedAt: nowMs,
    solUsd: quotes.sol,
    fxBrl: fxNow,
    note,
    periods,
    open: built?.open ?? [],
    sources: 'RPC Solana (getTransaction), CoinGecko SOL/USD, Frankfurter USD/BRL, DexScreener agora',
  };
}

interface SolPoint {
  t: number;
  usd: number;
}

interface FxPoint {
  date: string;
  brl: number;
}

interface QuoteBook {
  sol: number | null;
  mints: Map<string, { usd: number; symbol: string }>;
}

function makeMarks(solPoints: SolPoint[], fxSeries: FxPoint[], fxNow: number | null, quotes: QuoteBook): Marks {
  return {
    usd(asset, qty, ts) {
      if (asset === USDC || asset === USDT) return qty;
      if (asset === SOL) {
        const px = solAt(solPoints, ts);
        return px === null ? null : px * qty;
      }
      return null;
    },
    fx(ts) {
      return fxAt(fxSeries, ts);
    },
    currentUsd(asset, qty) {
      if (asset === USDC || asset === USDT) return qty;
      if (asset === SOL) return quotes.sol === null ? null : quotes.sol * qty;
      const row = quotes.mints.get(asset);
      return row ? row.usd * qty : null;
    },
    currentFx() {
      return fxNow;
    },
    symbol(mint) {
      return quotes.mints.get(mint)?.symbol ?? `${mint.slice(0, 4)}…`;
    },
  };
}

function solAt(points: SolPoint[], ts: number): number | null {
  if (!points.length) return null;
  let best = points[0];
  let dist = Math.abs(points[0].t - ts);
  for (const point of points) {
    const d = Math.abs(point.t - ts);
    if (d < dist) {
      best = point;
      dist = d;
    }
  }
  if (dist > 20 * 60) return null;
  return best.usd;
}

function fxAt(series: FxPoint[], ts: number): number | null {
  const day = brtDateString(ts * 1000);
  const eligible = series.filter((row) => row.date <= day);
  if (!eligible.length) return null;
  const best = eligible[eligible.length - 1];
  const gap = Math.round((Date.parse(`${day}T00:00:00Z`) - Date.parse(`${best.date}T00:00:00Z`)) / 86_400_000);
  if (gap > 4) return null;
  return best.brl;
}

async function fetchSolUsd(fromSec: number, toSec: number): Promise<SolPoint[]> {
  const url = `https://api.coingecko.com/api/v3/coins/solana/market_chart/range?vs_currency=usd&from=${Math.floor(fromSec)}&to=${Math.floor(toSec)}`;
  try {
    const body = await getJson(url);
    const prices = (body as { prices?: [number, number][] }).prices ?? [];
    if (prices.length) return prices.map(([ms, usd]) => ({ t: ms / 1000, usd }));
  } catch {
    // Cai para a Kraken se a CoinGecko recusar.
  }
  const kraken = await getJson('https://api.kraken.com/0/public/OHLC?pair=SOLUSD&interval=5');
  const rows = Object.values((kraken as { result?: Record<string, unknown> }).result ?? {}).find(Array.isArray) as
    | [number, string, string, string, string][]
    | undefined;
  return (rows ?? []).map((row) => ({ t: Number(row[0]), usd: Number(row[4]) }));
}

async function fetchFxSeries(fromMs: number, toMs: number): Promise<FxPoint[]> {
  const start = new Date(fromMs - 5 * 86_400_000).toISOString().slice(0, 10);
  const end = new Date(toMs).toISOString().slice(0, 10);
  const body = await getJson(`https://api.frankfurter.app/${start}..${end}?from=USD&to=BRL`);
  const rates = (body as { rates?: Record<string, { BRL?: number }> }).rates ?? {};
  return Object.entries(rates)
    .map(([date, row]) => ({ date, brl: Number(row.BRL) }))
    .filter((row) => Number.isFinite(row.brl))
    .sort((a, b) => a.date.localeCompare(b.date));
}

async function fetchFxNow(): Promise<number | null> {
  try {
    const body = await getJson('https://api.frankfurter.app/latest?from=USD&to=BRL');
    const brl = (body as { rates?: { BRL?: number } }).rates?.BRL;
    return typeof brl === 'number' ? brl : null;
  } catch {
    return null;
  }
}

async function fetchQuotes(balances: { tokens: { mint: string; qty: number }[] }): Promise<QuoteBook> {
  const mints = balances.tokens.filter((token) => token.qty > 0.001 && token.mint !== USDC && token.mint !== USDT).map((token) => token.mint);
  const book: QuoteBook = { sol: null, mints: new Map() };
  const [sol, ...rest] = await Promise.all([dexQuote(WSOL_MINT), ...mints.map((mint) => dexQuote(mint))]);
  book.sol = sol?.usd ?? null;
  mints.forEach((mint, i) => {
    const quote = rest[i];
    if (quote) book.mints.set(mint, quote);
  });
  return book;
}

async function dexQuote(mint: string): Promise<{ usd: number; symbol: string } | null> {
  const body = await getJson(`https://api.dexscreener.com/token-pairs/v1/solana/${mint}`);
  const pairs = Array.isArray(body) ? body : [];
  let best: { usd: number; symbol: string; liq: number } | null = null;
  for (const pair of pairs) {
    if (!pair || typeof pair !== 'object') continue;
    const row = pair as { baseToken?: { address?: string; symbol?: string }; priceUsd?: string; liquidity?: { usd?: number } };
    if (row.baseToken?.address !== mint) continue;
    const usd = Number(row.priceUsd);
    const liq = Number(row.liquidity?.usd ?? 0);
    if (!Number.isFinite(usd) || usd <= 0) continue;
    if (!best || liq > best.liq) best = { usd, symbol: row.baseToken.symbol || mint.slice(0, 4), liq };
  }
  return best ? { usd: best.usd, symbol: best.symbol } : null;
}

interface RawAccount {
  pubkey: string;
  account?: { lamports?: number; data?: { parsed?: { info?: { mint?: string; tokenAmount?: { uiAmountString?: string } } } } };
}

async function fetchBalances(wallet: string): Promise<{ sol: number; tokens: { mint: string; qty: number }[] }> {
  const [native, legacy, next] = await Promise.all([
    rpc<number>('getBalance', [wallet, { commitment: 'confirmed' }]).then((r) => (r as { value?: number }).value ?? (r as number)),
    tokenAccounts(wallet, TOKEN),
    tokenAccounts(wallet, TOKEN_2022),
  ]);
  const accounts = [...legacy, ...next];
  let rent = 0;
  let wsol = 0;
  const merged = new Map<string, number>();
  for (const row of accounts) {
    rent += row.account?.lamports ?? 0;
    const info = row.account?.data?.parsed?.info;
    const mint = info?.mint ?? '';
    const qty = Number(info?.tokenAmount?.uiAmountString ?? 0);
    if (mint === WSOL_MINT) wsol += qty;
    else if (mint) merged.set(mint, (merged.get(mint) ?? 0) + qty);
  }
  const sol = (typeof native === 'number' ? native : 0) / 1e9 + rent / 1e9 - wsol;
  return { sol, tokens: [...merged.entries()].map(([mint, qty]) => ({ mint, qty })) };
}

async function tokenAccounts(wallet: string, programId: string): Promise<RawAccount[]> {
  const result = await rpc<{ value?: RawAccount[] }>('getTokenAccountsByOwner', [wallet, { programId }, { encoding: 'jsonParsed', commitment: 'confirmed' }]);
  return result.value ?? [];
}

async function fetchHistory(wallet: string): Promise<ChainTx[]> {
  const accounts = [wallet];
  const [legacy, next] = await Promise.all([tokenAccounts(wallet, TOKEN), tokenAccounts(wallet, TOKEN_2022)]);
  for (const row of [...legacy, ...next]) if (row.pubkey) accounts.push(row.pubkey);
  const sigs = new Map<string, number | null>();
  for (const account of accounts) {
    let before: string | undefined;
    for (let page = 0; page < 10; page++) {
      const rows = await rpc<{ signature: string; blockTime: number | null; err: unknown }[]>('getSignaturesForAddress', [
        account,
        { limit: 1000, before, commitment: 'confirmed' },
      ]);
      if (!rows.length) break;
      for (const row of rows) if (!row.err) sigs.set(row.signature, row.blockTime);
      if (rows.length < 1000) break;
      before = rows[rows.length - 1].signature;
    }
  }
  const txs: ChainTx[] = [];
  await pool([...sigs.keys()], 8, async (signature) => {
    const tx = await rpc<ChainTx['tx'] | null>('getTransaction', [signature, { encoding: 'jsonParsed', commitment: 'confirmed', maxSupportedTransactionVersion: 1 }]);
    if (tx) txs.push({ signature, blockTime: sigs.get(signature) ?? null, tx });
  });
  if (txs.length !== sigs.size) throw new Error('o RPC não devolveu todas as transações; o painel não inventa o que falta');
  return txs;
}

async function pool<T>(items: T[], size: number, fn: (item: T) => Promise<void>): Promise<void> {
  let cursor = 0;
  await Promise.all(
    Array.from({ length: Math.min(size, items.length) }, async () => {
      while (cursor < items.length) {
        const item = items[cursor++];
        await fn(item);
      }
    }),
  );
}

async function rpc<T>(method: string, params: unknown[]): Promise<T> {
  let last = 'RPC indisponível';
  for (const url of RPCS) {
    for (let attempt = 0; attempt < 3; attempt++) {
      try {
        const res = await fetch(url, {
          method: 'POST',
          headers: { 'content-type': 'application/json', 'user-agent': UA },
          body: JSON.stringify({ jsonrpc: '2.0', id: 1, method, params }),
          signal: AbortSignal.timeout(20_000),
        });
        if (res.status === 429) {
          await sleep(400 * (attempt + 1));
          continue;
        }
        const body = (await res.json()) as { result?: T; error?: { message?: string } };
        if (body.error) {
          last = body.error.message ?? 'erro do RPC';
          await sleep(200);
          continue;
        }
        return body.result as T;
      } catch (error) {
        last = error instanceof Error ? error.message : 'erro do RPC';
        await sleep(200);
      }
    }
  }
  throw new Error(last);
}

async function getJson(url: string): Promise<unknown> {
  const res = await fetch(url, { headers: { accept: 'application/json', 'user-agent': UA }, signal: AbortSignal.timeout(20_000) });
  if (!res.ok) throw new Error(`${res.status} em ${new URL(url).host}`);
  return res.json();
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}
