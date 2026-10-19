import assert from 'node:assert/strict';
import test from 'node:test';
import { bestQuote, DACITY_MINT, formatPct, formatUsd, pumpMints, trendingQuotes } from './dex';

const dacity = {
  chainId: 'solana',
  dexId: 'pumpswap',
  url: 'https://dexscreener.com/solana/pair',
  baseToken: { address: DACITY_MINT, name: 'Dacity Coin', symbol: 'Dacity' },
  priceUsd: '0.007127',
  marketCap: 6997755,
  liquidity: { usd: 321425.68 },
  volume: { h24: 2835712.33 },
  priceChange: { h24: 108 },
};

test('$DACITY quote keeps price, cap, liquidity, volume and the 24h change', () => {
  const quote = bestQuote([dacity, { ...dacity, liquidity: { usd: 10 }, dexId: 'pumpfun' }], DACITY_MINT);
  assert.ok(quote);
  assert.equal(quote.symbol, 'Dacity');
  assert.equal(quote.priceUsd, 0.007127);
  assert.equal(quote.marketCap, 6997755);
  assert.equal(quote.liquidityUsd, 321425.68);
  assert.equal(quote.volumeH24, 2835712.33);
  assert.equal(quote.changeH24, 108);
  assert.equal(quote.dexId, 'pumpswap');
  assert.equal(formatUsd(quote.marketCap), '$7.00M');
  assert.equal(formatPct(quote.changeH24), '+108.00%');
});

test('trending keeps the DexScreener order and only Solana pump.fun mints', () => {
  const pump = 'Mint1111111111111111111111111111111111pump';
  const other = 'NotPump111111111111111111111111111111111111';
  const top = [
    { chainId: 'ethereum', tokenAddress: `${other}pump` },
    { chainId: 'solana', tokenAddress: pump },
    { chainId: 'solana', tokenAddress: other },
  ];
  const pairs = [
    {
      dexId: 'pumpswap',
      baseToken: { address: pump, symbol: 'POP', name: 'Pop' },
      priceUsd: '0.1',
      marketCap: 1000,
      liquidity: { usd: 50 },
      volume: { h24: 10 },
      priceChange: { h24: -2.5 },
    },
  ];
  assert.deepEqual(pumpMints(top), [pump]);
  const rows = trendingQuotes(top, [], pairs, 10);
  assert.equal(rows.length, 1);
  assert.equal(rows[0].symbol, 'POP');
  assert.equal(formatPct(rows[0].changeH24), '-2.50%');
});
