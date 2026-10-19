# crypto-daytrade

Live office for Bernardo's memecoin desk: https://iannini-daytrade.vercel.app

The site is `code-town/` (the Habblaud office). It reads Supabase `agent_events` and public DexScreener data. It does not sign transactions or store keys.

- `memecoins/` — read-only collectors (DexScreener and RugCheck) and the advisory protocol
- `legacy/` — retired Bybit paper desk, not part of the Vercel build
