# Day-trade playbook

Spot, long only, on a Brazil Bybit Standard Account. The account does not
trade perps or margin. The paper book is **19.9 USDT** (about R$100), funded
by a person via Pix. This file is how a person reads a chart. `python -m desk
scan` only labels the same rules. It does not send orders, and it does not
write the ledger unless `LEDGER_WRITER=1`.

The approved pattern catalog is the Portuguese playbook
[playbook-padroes-v1.md](playbook-padroes-v1.md) (v1, 2026-10-06). This page
follows it. Where the two differ, the Portuguese file wins.

## Filters that apply to every pattern

1. **Daily structure is higher highs and higher lows, and the daily close is
   above the 100-day average.** If either filter fails, there is no long.
2. **The pattern is drawn on the 1h or the daily chart.** The stop is that
   structure (last higher low, flag base, right shoulder, second bottom).
   A 15m swing is not a stop and a 15m shape is not the pattern. The 15m
   candle only confirms the entry: the close has to clear the level. A wick
   is not an entry.
3. **Session.** New entries are for 10:00–12:30 America/Sao_Paulo. Outside
   that window the picture is watch-only. A paper position may stay open
   overnight, for 1 to 5 days. The stop is live the whole time: every
   candle is checked, and a gap through the stop fills at the open. Past
   five days, the position is overdue and should be reviewed by a person.
4. **Round-trip cost is 0.30%.** That is VIP0 spot fees of 0.10% in and
   0.10% out (0.20%) plus 0.10% slippage. The gate uses

   ```
   net R:R = (target% - 0.30) / (stop% + 0.30)
   ```

   which means `target% >= 2 × stop% + 0.90`. A gross 2R is not enough.
   The floor is **6.9%** (that formula at a 3.0% stop). At a 9.66% stop the
   same formula asks for 20.22% (the playbook illustration rounds it to
   20.2%). Worked case: stop 3.5%, target 7.9% → (7.9 − 0.30) / (3.5 + 0.30) = 2.
5. **Cost versus the stop.** 0.30% has to be at most 10% of the stop
   distance, so the stop is at least **3.0%**. A 1% stop is rejected.
6. **Account size.** The minimum order is 6 USDT on this ~19.9 USDT book.
   Risk on that minimum order, including the 0.30% cost, has to stay within
   3% of equity. The gate prints the band:

   | Stop distance | Band |
   | --- | --- |
   | under 3.0% | rejected, cost rule |
   | 3.00% through 3.02% | 1% target zone |
   | above 3.02% through 9.66% | exception, needs justification |
   | above 9.66% | rejected |

   The 1% and 3% formulas are `(risk × 19.9 / 6) − 0.30` in percent. The 3%
   edge quantizes to 9.65; v1 keeps **9.66% inclusive**. Do not loosen them
   to force a trade. A valid structural stop sits in **3.0–9.66%** and at or
   under **3×ATR(D)**.
7. **3×ATR(D) is only a ceiling.** If the 1h or daily swing is farther than
   three daily ATRs from the entry, skip. Do not move the stop up to the
   ATR line to make it fit. Do not tighten a stop so it lands inside the
   pattern ("stop no meio do padrão"). If the structural low does not fit,
   the setup is out for this window.
8. **One loss ends the day.** After one losing close on the America/Sao_Paulo
   date, no new entries that day. At most **3 trades** that day, and one
   open position. No new risk at or below 90% of starting equity.

## Event locks

No new entries from 15 minutes before until 15 minutes after CPI, FOMC,
payroll, PCE, or GDP. Put those timestamps in the JSON file named by
`DESK_EVENTS_PATH`. Names are `CPI`, `FOMC`, `payroll`, `PCE`, and `GDP`.

Friday University of Michigan window: **10:45–11:15 America/Sao_Paulo**,
every Friday. Brazil does not observe daylight-saving time.

CPI on **14 October 2026 at 09:30 America/Sao_Paulo** stays on the desk
calendar even when `DESK_EVENTS_PATH` is empty.

## Pre-event protection

On a blocking-event day (CPI, payroll, PCE, GDP, FOMC) an open long is
checked on the paper book only inside a window. The default window is
**[T−25 minutes, T]**. The **06:05 America/Sao_Paulo** run is madrugada
mode: it may act from **00:00 BRT until T**. This replaces waiting until
15 minutes before the print. Outside that window the check is a noop,
unless a flatten is already pending.

- marked result under **+1.00R** closes the paper long (`pre-<event>`)
- **+1.00R** or better raises the stop to **entry × 1.003** and never lowers
  it (`breakeven_+1R_pre_evento`). **0.99R** is not enough to raise
- if that breakeven would sit at or above the live bid, or the 15m candles
  cannot be read, the long is closed (`stop_nao_elevavel`)
- a Bybit bid older than **120 seconds**, or no bid, is retried **3 times**.
  If it is still not fresh, the position is flagged
  `pendente_zerar_pre_evento` and is not closed. A later run closes it at a
  **fresh** bid with reason `execucao_atrasada`, and records
  `devia_zerar_utc`, `executado_utc`, `atraso_execucao_min`,
  `preco_ref_quando_devia`, `preco_execucao`, and `diferenca_pct`
- every run with a quote prints the collection time in BRT and the age in
  seconds

`+1R` uses the stop the trade was opened with, on the same net scale as the
gate: (gain% − 0.30) / (stop% + 0.30). Before any raise, candles are walked
with the old stop up to now, `ultimo_check_utc` is stamped, and only then
is `{old, new, at_utc, reason}` appended. A later walk uses the stop that
was in force at each candle's open. A gap through the stop fills at
min(open, stop), and the exit records `stop_usado`.

`desk.events.pre_event_action` still recommends close or raise inside the
±15 minute lock, so a missed scheduled check is not silent. It does not
fire for the whole event day. `paper-status` prints that recommendation.
The ledger changes only when `LEDGER_WRITER=1`. Nothing is sent to Bybit.

A bearish figure armed on the open long exits on the first **closed** 1h
candle whose close is under `figura_min`. The fill is min(that close, the
live bid); both prices are stored. If the same 1h candle also trades
through the stop, the stop wins.

The team protocol is [protocolo.md](protocolo.md).

## Patterns

Names and status come from
[playbook-padroes-v1.md](playbook-padroes-v1.md). Every active pattern is
drawn on **1h or daily**. A 15m swing is a record, not the stop, and a 15m
shape is not the setup. The 15m candle only confirms a **close** beyond the
level. A measured move that does not clear net R:R of 2, or a target under
6.9%, is a skip. Do not slide the stop and do not invent a farther target
to pass the gate.

### Active longs (paper candidates only)

| Pattern | Where it is drawn | 15m close |
| --- | --- | --- |
| Ascending triangle | 1h or daily, priority 1 | through the flat high |
| Bull flag | 1h or daily, priority 2; needs a pole | through the flag high |
| Rectangle | 1h or daily, upside breakout only; buying the base is out | through resistance |
| Falling wedge | 1h, pullback inside daily HH/HL, low priority | through the upper boundary |
| Inverse head and shoulders | daily or 1h, never a 15m pattern | above the neckline |
| Double bottom | daily or 1h, never a 15m pattern | through the neckline (the eixo) |

A daily chart that is not HH/HL, or a close under SMA100, turns every name
above into a flat. A conflict between the daily read and the 15m read is a
flat. A break of the daily uptrend line is a flat.

### Exit only (never a short, never a new long)

Descending triangle, rising wedge, bear flag, pennant down, head and
shoulders top, double top, rounded top. A close through the level while a
long is open is an exit. The gate rejects these names even when the side
says Buy. Nothing in this desk opens a short.

### Out of v1 (log only)

Symmetric triangle, pennant up, and cup and handle. A 15m cup is forbidden.
A daily cup is observation only, not an automatic paper candidate. Rounded
bottom is not a setup.

## What the scanner is allowed to say

`python -m desk scan` can print `ignore`, `watch`, `exit_only`, or
`paper_candidate`.

`paper_candidate` means an **active** long drawn on 1h or daily, the daily
filters, the 1h or daily stop inside 3.0–9.66% and at or under 3×ATR(D),
the target floor, a 15m close through the level, the Sao Paulo window, the
event locks, the loss lock, the three-trade cap, and the cost gate all
passed on a coarse heuristic. It is a note for a person. The process does
not size a live order and does not call the exchange. `exit_only` means the
label must not open a short and must not open a new long.

Heuristics miss patterns and mislabel them. If the chart disagrees with the
label, the chart wins, and the trade is still skipped when the gate fails.
