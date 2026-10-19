// Leitura pública do DexScreener. Sem chave, sem ordem, sem carteira.

export const DACITY_MINT = 'nxPqZ4F7ux8Vph5NFu25rEP6Kx9Gr1U6Fmj36Rjpump';
const DEX = 'https://api.dexscreener.com';

export interface TokenQuote {
  symbol: string;
  name: string;
  mint: string;
  priceUsd: number | null;
  marketCap: number | null;
  liquidityUsd: number | null;
  volumeH24: number | null;
  changeH24: number | null;
  url: string;
  dexId: string;
}

export function dacityPairsUrl(): string {
  return `${DEX}/token-pairs/v1/solana/${DACITY_MINT}`;
}

export function boostsTopUrl(): string {
  return `${DEX}/token-boosts/top/v1`;
}

export function boostsLatestUrl(): string {
  return `${DEX}/token-boosts/latest/v1`;
}

export function tokensUrl(mints: string[]): string {
  return `${DEX}/tokens/v1/solana/${mints.join(',')}`;
}

function num(value: unknown): number | null {
  if (typeof value === 'number' && Number.isFinite(value)) return value;
  if (typeof value === 'string' && value.trim() && Number.isFinite(Number(value))) return Number(value);
  return null;
}

function asRecord(value: unknown): Record<string, unknown> | null {
  return value && typeof value === 'object' ? (value as Record<string, unknown>) : null;
}

export function quoteFromPair(pair: unknown, mintHint = ''): TokenQuote | null {
  const row = asRecord(pair);
  if (!row) return null;
  const base = asRecord(row.baseToken);
  const mint = (typeof base?.address === 'string' && base.address) || mintHint;
  if (!mint) return null;
  const volume = asRecord(row.volume);
  const change = asRecord(row.priceChange);
  const liquidity = asRecord(row.liquidity);
  return {
    symbol: typeof base?.symbol === 'string' && base.symbol ? base.symbol : '?',
    name: typeof base?.name === 'string' && base.name ? base.name : '',
    mint,
    priceUsd: num(row.priceUsd),
    marketCap: num(row.marketCap) ?? num(row.fdv),
    liquidityUsd: num(liquidity?.usd),
    volumeH24: num(volume?.h24),
    changeH24: num(change?.h24),
    url: typeof row.url === 'string' ? row.url : `https://dexscreener.com/solana/${mint}`,
    dexId: typeof row.dexId === 'string' ? row.dexId : '',
  };
}

/** The deepest pool wins so a thin pair does not replace the tradable quote. */
export function bestQuote(pairs: unknown, mint = ''): TokenQuote | null {
  const list = Array.isArray(pairs) ? pairs : [];
  let best: TokenQuote | null = null;
  for (const pair of list) {
    const quote = quoteFromPair(pair, mint);
    if (!quote) continue;
    if (mint && quote.mint !== mint) continue;
    if (!best || (quote.liquidityUsd ?? -1) > (best.liquidityUsd ?? -1)) best = quote;
  }
  return best;
}

/** Solana mints launched on pump.fun, in the order DexScreener already ranked them. */
export function pumpMints(rows: unknown): string[] {
  if (!Array.isArray(rows)) return [];
  const out: string[] = [];
  const seen = new Set<string>();
  for (const row of rows) {
    const rec = asRecord(row);
    if (!rec || rec.chainId !== 'solana') continue;
    const addr = typeof rec.tokenAddress === 'string' ? rec.tokenAddress : '';
    if (!addr.endsWith('pump') || seen.has(addr)) continue;
    seen.add(addr);
    out.push(addr);
  }
  return out;
}

export function rankedPumpMints(top: unknown, latest: unknown, limit = 30): string[] {
  const mints = pumpMints(top);
  for (const mint of pumpMints(latest)) if (!mints.includes(mint)) mints.push(mint);
  return mints.slice(0, limit);
}

export function trendingQuotes(top: unknown, latest: unknown, pairs: unknown, limit = 10): TokenQuote[] {
  const mints = rankedPumpMints(top, latest, Math.max(limit, 30));
  const byMint = new Map<string, TokenQuote>();
  const list = Array.isArray(pairs) ? pairs : [];
  for (const mint of mints) {
    const quote = bestQuote(list, mint);
    if (quote) byMint.set(mint, quote);
  }
  return mints.filter((mint) => byMint.has(mint)).slice(0, limit).map((mint) => byMint.get(mint)!);
}

export function formatUsd(value: number | null): string {
  if (value == null || !Number.isFinite(value)) return '—';
  const abs = Math.abs(value);
  const sign = value < 0 ? '-' : '';
  if (abs >= 1_000_000_000) return `${sign}$${(abs / 1_000_000_000).toFixed(2)}B`;
  if (abs >= 1_000_000) return `${sign}$${(abs / 1_000_000).toFixed(2)}M`;
  if (abs >= 1_000) return `${sign}$${(abs / 1_000).toFixed(1)}k`;
  if (abs >= 1) return `${sign}$${abs.toFixed(2)}`;
  if (abs >= 0.01) return `${sign}$${abs.toFixed(4)}`;
  return `${sign}$${abs.toPrecision(3)}`;
}

export function formatPct(value: number | null): string {
  if (value == null || !Number.isFinite(value)) return '—';
  const sign = value > 0 ? '+' : '';
  return `${sign}${value.toFixed(2)}%`;
}
