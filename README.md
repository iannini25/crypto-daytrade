# Crypto day-trade desk

Paper desk for Bernardo: Brazil, Bybit **Standard Account**, spot only,
about **R$100 / US$20**. Perps and margin are out (the Brazil account no
longer offers them). Funding in reais is a **human Pix deposit**. This
repository does not move money and does not talk to Pix.

**There is no unattended live trading.** The programs below read public
market data and a local JSON ledger. They do not sign requests and they do
not post orders. `LIVE_ORDERS_CONFIRM` defaults to `false`. The only value
that unlocks anything is the word `yes`, and that only prints a text ticket
for a person to read (`desk.orders.manual_order_ticket`). `submit_live_order`
always raises. A human yes is still required before anyone types an order
into the Bybit website, and this repo will not type it for them.

## Desk rules

| Rule | Value |
| --- | --- |
| Market | Spot USDT majors: BTC, ETH, SOL |
| Direction | Long only |
| Timeframes | Daily HH/HL and close above SMA100. Stop on a 1h or daily swing. 15m close only times the entry. 3×ATR(D) is a ceiling, not a stop |
| Session | New entries 10:00–12:30 America/Sao_Paulo. Overnight holds are allowed (swing 1–5 days, paper) |
| Cost | VIP0 0.20% fees + 0.10% slippage = **0.30% round trip** |
| Payoff | Net R:R = (target% − 0.30) / (stop% + 0.30) ≥ 2, i.e. target% ≥ 2×stop% + 0.90, with a **6.9%** target floor |
| Stop | Structural 1h or daily stop in **3.0–9.66%** and at or under 3×ATR(D). 3.00–3.02% is the 1% zone; above 3.02% through 9.66% needs justification; above 9.66% is rejected. Do not tighten a stop into the middle of the pattern |
| Day stop | One losing trade ends new entries for that Sao Paulo day. At most 3 trades. One position |
| Events | No new entries ±15 minutes around CPI, FOMC, payroll, PCE. Friday UoM lock 10:45–11:15 BRT. Under +1R, close 15 minutes before; at +1R, stop to entry+costs and hold |
| Kill | No new risk at or below 90% of starting equity |
| Ledger | Read-only unless `LEDGER_WRITER=1`, and then an exclusive file lock |

Pattern notes are in [docs/playbook.md](docs/playbook.md). The approved
catalog (Portuguese, v1) is
[docs/playbook-padroes-v1.md](docs/playbook-padroes-v1.md): active patterns
are long-only; exit-only patterns never open a short or a new long; 15m
only confirms a close. A 1R measured move does not clear the fee gate.
Skip it.

Environment variables can make risk, the kill switch, or the R:R floor
**stricter**. They cannot loosen them. `DESK_CATEGORY` other than `spot` is
rejected.

## Run the monitors

Python 3.11 or newer. No API key.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

python -m desk snapshot      # public ticker, order book, 15m and 1d closes
python -m desk paper-status  # simulated USDT ledger and the risk limits
python -m desk scan          # dry-run labels; never posts an order
pytest
```

`paper-status --init` writes `data/paper_ledger.json` (gitignored) only when
`LEDGER_WRITER=1`. Without that flag the command is a dry run and does not
create the file. The default paper equity is 19.9 USDT. `DESK_BRL_PER_USDT`
(default 5) is a display hint so that book reads as about R$100. It is not a
live FX rate.

Optional flags: `--json` on each command, `--ledger PATH` on `paper-status`
and `scan`.

Bybit's CDN returns HTTP 403 for some datacenter regions. That is a country
block, not a missing key. Run the monitors from a network Bybit serves (a
home connection in Brazil). There is no scheduled GitHub snapshot for that
reason: hosted runners are often blocked. `.github/workflows/tests.yml`
runs the offline tests only.

Public REST only, via `desk.bybit`:

- `GET /v5/market/tickers`
- `GET /v5/market/kline`
- `GET /v5/market/orderbook`

Category is forced to `spot`. The unfinished candle is dropped so "close
confirms" means a finished bar.

## Secrets

Copy `.env.example` to `.env` if you want blanks filled in later. Do not
commit `.env`. Placeholders:

- `BYBIT_API_KEY` and `BYBIT_API_SECRET` (Bybit HMAC pair)
- `BYBIT_AI_SUBACCOUNT_ID`

`paper-status` prints whether each one is set, not the value. Nothing in
the monitors sends them.

## Layout

```
desk/           config, public client, fees, risk gate, paper ledger, scanner
docs/playbook.md
docs/playbook-padroes-v1.md
tests/          fee math, R:R after fees, gates, public client
.github/workflows/tests.yml
```

## Paper ledger helpers

`desk.paper.open_long` and `close_long` adjust the local ledger when the
risk gate allows it. They are not wired to a trading CLI and they do not
call Bybit. `scan` does not open paper trades by itself; a
`paper_candidate` line is a note, not a fill.
