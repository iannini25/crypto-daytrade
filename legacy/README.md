# Legacy desk (not built, not live)

These trees are the old paper desk. They are archived so the office build does not run them. Vercel builds `code-town/` only.

The git history of this repository has two retired Bybit paper desks and no separate Coinbase or SPRINT package. `bybit-paper/` is the last paper desk (public Bybit market data and a local JSON ledger). `trading-system/` is the earlier Bybit paper engine and its backtests. That is the Coinbase/SPRINT/Bybit era this office replaced: the live site no longer imports either tree.

Do not deploy this folder. Do not put a key, seed, or secret in it. The programs were paper monitors; the memecoin desk does not call them. Nothing here is wired to https://iannini-daytrade.vercel.app.

The live desk is advisory and lives in `memecoins/` plus the office in `code-town/`. It does not sign transactions.
