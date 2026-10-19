// Carteira pump.fun só de leitura. Os números nascem no servidor; a barra só exibe.

export const PUMP_WALLET = '3QBHDouo2b1NxnqCoKkkUqpPCPZwVJQvrTNAFGEkzZ1q';

export const SOL = 'SOL';
export const USDC = 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v';
export const USDT = 'Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB';
export const WSOL_MINT = 'So11111111111111111111111111111111111111112';

export type PeriodKey = 'day' | 'week' | 'all';

export interface Leg {
  asset: string;
  qty: number;
}

export type WalletEvent =
  | { kind: 'deposit'; ts: number; sig: string; ord: number; asset: string; qty: number }
  | { kind: 'withdraw'; ts: number; sig: string; ord: number; asset: string; qty: number }
  | { kind: 'buy'; ts: number; sig: string; ord: number; mint: string; qty: number; spent: Leg[]; rebate: Leg[] }
  | { kind: 'sell'; ts: number; sig: string; ord: number; mint: string; qty: number; got: Leg[]; fees: Leg[] }
  | { kind: 'convert'; ts: number; sig: string; ord: number; spent: Leg; got: Leg }
  | { kind: 'unclassified'; ts: number; sig: string; ord: number; reason: string };

export interface Figure {
  usd: number | null;
  brl: number | null;
  /** Preenchido quando o número não dá para afirmar. A barra mostra "—". */
  reason?: string;
}

export interface OpenPosition {
  mint: string;
  symbol: string;
  qty: number;
  avgUsd: number | null;
  priceUsd: number | null;
  pnlUsd: number | null;
  pnlBrl: number | null;
  reason?: string;
}

export interface PeriodFigures {
  investido: Figure;
  aportes: Figure;
  prejuizo: Figure;
  lucro: Figure;
  aberto: Figure;
}

export interface WalletPnl {
  ok: boolean;
  wallet: string;
  computedAt: number;
  solUsd: number | null;
  fxBrl: number | null;
  /** Texto curto para a dica do filtro. */
  note: string;
  periods: Record<PeriodKey, PeriodFigures>;
  open: OpenPosition[];
  sources: string;
}

export function isQuote(asset: string): boolean {
  return asset === SOL || asset === USDC || asset === USDT;
}

export function emptyFigure(reason: string): Figure {
  return { usd: null, brl: null, reason };
}

export function figure(usd: number, brl: number): Figure {
  return { usd, brl };
}
