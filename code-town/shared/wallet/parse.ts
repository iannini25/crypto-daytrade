// Lê uma transação jsonParsed e separa depósito, retirada, compra, venda e conversão.
// Custo do token = SOL/USDC que saiu na troca, com a taxa da rede, a gorjeta e a taxa da plataforma.
// O aluguel que fica numa conta de token ainda aberta continua sendo SOL da carteira, não custo do token.

import { SOL, USDC, USDT, WSOL_MINT, isQuote, type Leg, type WalletEvent } from './types';

const DUST_TOKEN = 1e-4;
const SOL_FEE_CAP = 0.005;
const STABLE_FEE_CAP = 0.1;
const FEE_RATIO = 0.02;

interface RpcTokenAmount {
  amount?: string;
  decimals?: number;
  uiAmount?: number | null;
  uiAmountString?: string | null;
}

interface RpcTokenBalance {
  accountIndex: number;
  mint: string;
  owner?: string;
  uiTokenAmount?: RpcTokenAmount;
}

interface RpcIx {
  programId?: string;
  program?: string;
  parsed?: { type?: string; info?: Record<string, unknown> } | string;
}

interface RpcTx {
  transaction?: { message?: { accountKeys?: unknown[]; instructions?: RpcIx[] } };
  meta?: {
    fee?: number;
    err?: unknown;
    preBalances?: number[];
    postBalances?: number[];
    preTokenBalances?: RpcTokenBalance[];
    postTokenBalances?: RpcTokenBalance[];
    innerInstructions?: { index: number; instructions?: RpcIx[] }[];
  };
}

export interface ChainTx {
  signature: string;
  blockTime: number | null;
  tx: RpcTx;
}

interface Flow {
  group: number;
  asset: string;
  qty: number;
}

function asInfo(ix: RpcIx): { type: string; info: Record<string, unknown> } | null {
  const parsed = ix.parsed;
  if (!parsed || typeof parsed === 'string') return null;
  if (!parsed.type || !parsed.info || typeof parsed.info !== 'object') return null;
  return { type: parsed.type, info: parsed.info };
}

function keysOf(tx: RpcTx): string[] {
  const keys = tx.transaction?.message?.accountKeys ?? [];
  return keys.map((k) => (typeof k === 'string' ? k : String((k as { pubkey?: string }).pubkey ?? '')));
}

function uiOf(amount: RpcTokenAmount | undefined): number {
  if (!amount) return 0;
  if (typeof amount.uiAmountString === 'string' && amount.uiAmountString) return Number(amount.uiAmountString);
  if (typeof amount.uiAmount === 'number') return amount.uiAmount;
  return 0;
}

function rawAmount(info: Record<string, unknown>, decimals: number): number {
  const tokenAmount = info.tokenAmount as RpcTokenAmount | undefined;
  if (tokenAmount?.amount !== undefined) return Number(tokenAmount.amount);
  if (typeof info.amount === 'string' || typeof info.amount === 'number') return Number(info.amount);
  return Math.round(qtyOf(info, decimals) * 10 ** decimals);
}

function qtyOf(info: Record<string, unknown>, decimals: number): number {
  const tokenAmount = info.tokenAmount as RpcTokenAmount | undefined;
  if (tokenAmount) return uiOf(tokenAmount);
  const raw = info.amount;
  if (typeof raw === 'string' || typeof raw === 'number') return Number(raw) / 10 ** decimals;
  return 0;
}

function eachIx(tx: RpcTx, fn: (group: number, ix: RpcIx) => void): void {
  const outer = tx.transaction?.message?.instructions ?? [];
  const inner = new Map<number, RpcIx[]>();
  for (const group of tx.meta?.innerInstructions ?? []) inner.set(group.index, group.instructions ?? []);
  outer.forEach((ix, index) => {
    fn(index, ix);
    for (const child of inner.get(index) ?? []) fn(index, child);
  });
}

function isStable(asset: string): boolean {
  return asset === USDC || asset === USDT;
}

function quoteGross(map: Map<string, number>): number {
  let gross = 0;
  for (const [asset, qty] of map) if (isQuote(asset)) gross += Math.abs(qty);
  return gross;
}

function isSmallFee(asset: string, qty: number, trade: Map<string, number> | null): boolean {
  const out = Math.abs(qty);
  if (asset === SOL && out <= SOL_FEE_CAP) return true;
  if (isStable(asset) && out <= STABLE_FEE_CAP) return true;
  if (trade) {
    const gross = quoteGross(trade);
    if (gross > 0 && out <= gross * FEE_RATIO && isQuote(asset)) return true;
  }
  return false;
}

function legs(map: Map<string, number>, sign: 1 | -1): Leg[] {
  const out: Leg[] = [];
  for (const [asset, qty] of map) {
    if (Math.sign(qty) !== sign) continue;
    if (Math.abs(qty) < 1e-10) continue;
    out.push({ asset, qty: Math.abs(qty) });
  }
  return out;
}

/**
 * Converte as transações em eventos na ordem cronológica.
 * `problems` lista o que impediu um número confiável (a barra então mostra "—").
 */
export function parseWalletTxs(txs: ChainTx[], wallet: string): { events: WalletEvent[]; problems: string[] } {
  const ordered = [...txs].sort((a, b) => (a.blockTime ?? 0) - (b.blockTime ?? 0) || a.signature.localeCompare(b.signature));
  const events: WalletEvent[] = [];
  const problems: string[] = [];
  for (const tx of ordered) {
    const parsed = parseOne(tx, wallet);
    if (parsed.problem) problems.push(parsed.problem);
    events.push(...parsed.events);
  }
  return { events, problems };
}

function parseOne(item: ChainTx, wallet: string): { events: WalletEvent[]; problem: string | null } {
  const sig = item.signature;
  const ts = item.blockTime ?? 0;
  if (!item.blockTime) {
    return { events: [unclassified(sig, ts, 0, 'transação sem horário')], problem: `${short(sig)} sem horário` };
  }
  if (item.tx.meta?.err) return { events: [], problem: null };

  const keys = keysOf(item.tx);
  const pre = item.tx.meta?.preBalances ?? [];
  const post = item.tx.meta?.postBalances ?? [];
  if (pre.length !== keys.length || post.length !== keys.length) {
    return fail(sig, ts, 'os saldos e as contas da transação não batem');
  }
  const indexOf = new Map(keys.map((k, i) => [k, i]));
  const walletIndex = indexOf.get(wallet);

  const decimals = new Map<string, number>();
  const owned = new Set<string>();
  const mintOf = new Map<string, string>();
  const absorb = (rows: RpcTokenBalance[] | undefined) => {
    for (const row of rows ?? []) {
      const pubkey = keys[row.accountIndex];
      if (!pubkey) continue;
      decimals.set(row.mint, row.uiTokenAmount?.decimals ?? decimals.get(row.mint) ?? 0);
      if (row.owner === wallet) {
        owned.add(pubkey);
        mintOf.set(pubkey, row.mint);
      }
    }
  };
  absorb(item.tx.meta?.preTokenBalances);
  absorb(item.tx.meta?.postTokenBalances);

  const closed = new Set<string>();
  eachIx(item.tx, (_group, ix) => {
    const parsed = asInfo(ix);
    if (!parsed) return;
    if (parsed.type === 'initializeAccount3' || parsed.type === 'initializeAccount') {
      const owner = String(parsed.info.owner ?? '');
      const account = String(parsed.info.account ?? '');
      const mint = String(parsed.info.mint ?? '');
      if (owner === wallet && account) {
        owned.add(account);
        if (mint) mintOf.set(account, mint);
      }
    }
    if (parsed.type === 'closeAccount') closed.add(String(parsed.info.account ?? ''));
  });

  const tokenDelta = new Map<string, number>();
  const addDelta = (rows: RpcTokenBalance[] | undefined, sign: 1 | -1) => {
    for (const row of rows ?? []) {
      if (row.owner !== wallet || row.mint === WSOL_MINT) continue;
      tokenDelta.set(row.mint, (tokenDelta.get(row.mint) ?? 0) + sign * uiOf(row.uiTokenAmount));
    }
  };
  addDelta(item.tx.meta?.preTokenBalances, -1);
  addDelta(item.tx.meta?.postTokenBalances, 1);

  const flows: Flow[] = [];
  const tokenFlows = new Map<string, number>();
  let rentRetained = 0;
  let rentReleased = 0;
  const born = new Set<string>();
  // Lamports no fim de cada instrução. Conta criada no meio da transação começa em zero.
  const lam = pre.slice();
  const feePayer = keys[0] === wallet;
  const fee = item.tx.meta?.fee ?? 0;
  if (feePayer && fee) {
    lam[0] -= fee;
    flows.push({ group: 10_000, asset: SOL, qty: -fee / 1e9 });
  }

  const noteToken = (mint: string, qty: number) => {
    if (mint === WSOL_MINT) return;
    tokenFlows.set(mint, (tokenFlows.get(mint) ?? 0) + qty);
  };
  const moveLamports = (source: string, destination: string, lamports: number) => {
    const from = indexOf.get(source);
    const to = indexOf.get(destination);
    if (from !== undefined) lam[from] -= lamports;
    if (to !== undefined) lam[to] += lamports;
  };

  eachIx(item.tx, (group, ix) => {
    const parsed = asInfo(ix);
    if (!parsed) return;
    const info = parsed.info;
    if (parsed.type === 'transfer' && (ix.program === 'system' || ix.programId === '11111111111111111111111111111111')) {
      const lamports = Number(info.lamports ?? 0);
      const source = String(info.source ?? '');
      const destination = String(info.destination ?? '');
      moveLamports(source, destination, lamports);
      if (source === wallet && mintOf.get(destination) === WSOL_MINT) return;
      if (source === wallet) flows.push({ group, asset: SOL, qty: -lamports / 1e9 });
      else if (destination === wallet) flows.push({ group, asset: SOL, qty: lamports / 1e9 });
      return;
    }
    if (parsed.type === 'createAccount') {
      const lamports = Number(info.lamports ?? 0);
      const source = String(info.source ?? '');
      const account = String(info.newAccount ?? '');
      born.add(account);
      moveLamports(source, account, lamports);
      if (source === wallet && owned.has(account) && !closed.has(account)) rentRetained += lamports;
      if (source === wallet && !owned.has(account)) flows.push({ group, asset: SOL, qty: -lamports / 1e9 });
      return;
    }
    if (parsed.type === 'closeAccount') {
      const account = String(info.account ?? '');
      const destination = String(info.destination ?? '');
      const idx = indexOf.get(account);
      const returning = idx === undefined ? 0 : lam[idx] ?? 0;
      if (idx !== undefined) lam[idx] = 0;
      const destIdx = indexOf.get(destination);
      if (destIdx !== undefined) lam[destIdx] += returning;
      if (destination === wallet && owned.has(account) && !born.has(account)) rentReleased += returning;
      if (destination === wallet && !owned.has(account) && returning) flows.push({ group, asset: SOL, qty: returning / 1e9 });
      return;
    }
    if (parsed.type === 'transfer' || parsed.type === 'transferChecked') {
      const source = String(info.source ?? '');
      const destination = String(info.destination ?? '');
      const sourceOwned = owned.has(source);
      const destOwned = owned.has(destination);
      const mint = String(info.mint ?? mintOf.get(source) ?? mintOf.get(destination) ?? '');
      const dec = decimals.get(mint) ?? (mint === WSOL_MINT ? 9 : isStable(mint) ? 6 : -1);
      if (mint === WSOL_MINT && dec >= 0) moveLamports(source, destination, rawAmount(info, dec));
      if (!sourceOwned && !destOwned) return;
      if (!mint || dec < 0) {
        flows.push({ group, asset: `unknown:${source}`, qty: 0 });
        return;
      }
      const qty = qtyOf(info, dec);
      const asset = mint === WSOL_MINT ? SOL : mint;
      if (sourceOwned && !destOwned) {
        flows.push({ group, asset, qty: -qty });
        noteToken(mint, -qty);
      } else if (destOwned && !sourceOwned) {
        flows.push({ group, asset, qty });
        noteToken(mint, qty);
      }
    }
  });

  const nativeDelta = walletIndex === undefined ? 0 : ((post[walletIndex] ?? 0) - (pre[walletIndex] ?? 0)) / 1e9;
  if (walletIndex !== undefined && Math.abs((lam[walletIndex] ?? 0) - (post[walletIndex] ?? 0)) > 2) {
    return fail(
      sig,
      ts,
      `o SOL movimentado (${((lam[walletIndex] ?? 0) - (pre[walletIndex] ?? 0)) / 1e9}) não fecha com o saldo (${nativeDelta.toFixed(9)})`,
    );
  }
  for (const [mint, delta] of tokenDelta) {
    const got = tokenFlows.get(mint) ?? 0;
    if (Math.abs(got - delta) > 1e-4) {
      return fail(sig, ts, `o token ${mint.slice(0, 4)}… não fecha (${got} calculado, ${delta} no saldo)`);
    }
  }
  for (const [mint, got] of tokenFlows) {
    const delta = tokenDelta.get(mint) ?? 0;
    if (Math.abs(got - delta) > 1e-4) {
      return fail(sig, ts, `movimento extra de ${mint.slice(0, 4)}…`);
    }
  }

  const grouped = new Map<number, Map<string, number>>();
  for (const flow of flows) {
    if (flow.asset.startsWith('unknown:')) return fail(sig, ts, 'transferência de token sem decimais');
    const bucket = grouped.get(flow.group) ?? new Map<string, number>();
    bucket.set(flow.asset, (bucket.get(flow.asset) ?? 0) + flow.qty);
    grouped.set(flow.group, bucket);
  }
  for (const bucket of grouped.values()) {
    for (const [asset, qty] of bucket) if (Math.abs(qty) < 1e-9) bucket.delete(asset);
  }

  const tradeIds = [...grouped.keys()].filter((id) => {
    const bucket = grouped.get(id)!;
    let pos = false;
    let neg = false;
    for (const qty of bucket.values()) {
      if (qty > 0) pos = true;
      if (qty < 0) neg = true;
    }
    return pos && neg;
  });
  const primary = tradeIds.sort((a, b) => quoteGross(grouped.get(b)!) - quoteGross(grouped.get(a)!))[0];
  const trade = primary === undefined ? null : grouped.get(primary)!;

  for (const [id, bucket] of [...grouped.entries()]) {
    if (tradeIds.includes(id) || !trade) continue;
    const entries = [...bucket.entries()];
    if (entries.length === 1 && entries[0][1] < 0 && isQuote(entries[0][0]) && isSmallFee(entries[0][0], entries[0][1], trade)) {
      const [asset, qty] = entries[0];
      trade.set(asset, (trade.get(asset) ?? 0) + qty);
      grouped.delete(id);
    }
  }

  const events: WalletEvent[] = [];
  let ord = 0;
  const ids = [...grouped.keys()].sort((a, b) => a - b);
  for (const id of ids) {
    const bucket = grouped.get(id)!;
    for (const [asset, qty] of [...bucket.entries()]) if (Math.abs(qty) < 1e-9) bucket.delete(asset);
    if (bucket.size === 0) continue;
    const built = classify(bucket);
    if (built === 'ignore') continue;
    if (built === 'bad') return fail(sig, ts, 'troca com mais de um token, sem um preço para dividir o custo');
    events.push({ ...built, ts, sig, ord: ord++ });
  }

  // O SOL econômico (sem o aluguel retido) tem de explicar o saldo nativo.
  let economic = 0;
  for (const ev of events) {
    if (ev.kind === 'deposit' && ev.asset === SOL) economic += ev.qty;
    if (ev.kind === 'withdraw' && ev.asset === SOL) economic -= ev.qty;
    if (ev.kind === 'buy') {
      for (const leg of ev.spent) if (leg.asset === SOL) economic -= leg.qty;
      for (const leg of ev.rebate) if (leg.asset === SOL) economic += leg.qty;
    }
    if (ev.kind === 'sell') {
      for (const leg of ev.got) if (leg.asset === SOL) economic += leg.qty;
      for (const leg of ev.fees) if (leg.asset === SOL) economic -= leg.qty;
    }
    if (ev.kind === 'convert') {
      if (ev.spent.asset === SOL) economic -= ev.spent.qty;
      if (ev.got.asset === SOL) economic += ev.got.qty;
    }
  }
  const expected = nativeDelta + rentRetained / 1e9 - rentReleased / 1e9;
  if (Math.abs(economic - expected) > 5e-6) {
    return fail(sig, ts, `o SOL da troca (${economic.toFixed(6)}) não fecha com o saldo depois do aluguel (${expected.toFixed(6)})`);
  }
  return { events, problem: null };
}

function fail(sig: string, ts: number, reason: string): { events: WalletEvent[]; problem: string } {
  return { events: [unclassified(sig, ts, 0, reason)], problem: `${short(sig)}: ${reason}` };
}

function unclassified(sig: string, ts: number, ord: number, reason: string): WalletEvent {
  return { kind: 'unclassified', ts, sig, ord, reason };
}

function short(sig: string): string {
  return `${sig.slice(0, 8)}…`;
}

type Classified =
  | { kind: 'deposit'; asset: string; qty: number }
  | { kind: 'withdraw'; asset: string; qty: number }
  | { kind: 'buy'; mint: string; qty: number; spent: Leg[]; rebate: Leg[] }
  | { kind: 'sell'; mint: string; qty: number; got: Leg[]; fees: Leg[] }
  | { kind: 'convert'; spent: Leg; got: Leg };

function classify(bucket: Map<string, number>): Classified | 'ignore' | 'bad' {
  const memeIn = legs(bucket, 1).filter((leg) => !isQuote(leg.asset));
  const memeOut = legs(bucket, -1).filter((leg) => !isQuote(leg.asset));
  const quoteIn = legs(bucket, 1).filter((leg) => isQuote(leg.asset));
  const quoteOut = legs(bucket, -1).filter((leg) => isQuote(leg.asset));
  const dust = (legs: Leg[]) => legs.every((leg) => leg.qty < DUST_TOKEN);

  if (memeIn.length === 0 && memeOut.length === 0) {
    if (quoteIn.length === 1 && quoteOut.length === 0) return { kind: 'deposit', asset: quoteIn[0].asset, qty: quoteIn[0].qty };
    if (quoteOut.length === 1 && quoteIn.length === 0) return { kind: 'withdraw', asset: quoteOut[0].asset, qty: quoteOut[0].qty };
    if (quoteIn.length === 1 && quoteOut.length === 1) return { kind: 'convert', spent: quoteOut[0], got: quoteIn[0] };
    if (quoteIn.length === 0 && quoteOut.length === 0) return 'ignore';
    return 'bad';
  }
  if (memeIn.length === 1 && memeOut.length === 0 && quoteOut.length >= 1) {
    return { kind: 'buy', mint: memeIn[0].asset, qty: memeIn[0].qty, spent: quoteOut, rebate: quoteIn };
  }
  if (memeOut.length === 1 && memeIn.length === 0 && (quoteIn.length >= 1 || quoteOut.length >= 1)) {
    return { kind: 'sell', mint: memeOut[0].asset, qty: memeOut[0].qty, got: quoteIn, fees: quoteOut };
  }
  if ((dust(memeIn) && dust(memeOut)) && quoteIn.length + quoteOut.length === 0) return 'ignore';
  return 'bad';
}
