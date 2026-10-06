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
2. **The stop anchors on a 1h or daily swing low.** A 15m swing is not a
   stop. The 15m candle only times the entry: the close has to clear the
   level. A wick is not an entry.
3. **Session.** New entries are for 10:00–12:30 America/Sao_Paulo. Outside
   that window the picture is watch-only. Holding overnight is allowed.
   The intended swing is 1 to 5 days, on the paper book. Past five days,
   the position is overdue and should be reviewed by a person.
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
payroll, or PCE. Put those timestamps in the JSON file named by
`DESK_EVENTS_PATH`. Names are `CPI`, `FOMC`, `payroll`, and `PCE`.

Friday University of Michigan window: **10:45–11:15 America/Sao_Paulo**,
every Friday. Brazil does not observe daylight-saving time.

Fifteen minutes before a lock (and during it, if the position is still
open):

- if the open long is under **+1R** on the same net-R scale, close it on
  the paper book
- if it is at **+1R** or better, move the stop to **entry + 0.30%** (entry
  plus the round-trip cost) and hold

`paper-status` prints that recommendation. It changes the ledger only when
`LEDGER_WRITER=1`. Nothing is sent to Bybit.

## Patterns

Names and status come from
[playbook-padroes-v1.md](playbook-padroes-v1.md). The stop is the 1h or
daily structure of the pattern (last higher low, flag base, right shoulder,
second bottom). A 15m swing is a record, not that stop. The 15m candle only
confirms a **close** beyond the level. A measured move that does not clear
net R:R of 2, or a target under 6.9%, is a skip. Do not slide the stop and
do not invent a farther target to pass the gate.

### Active longs (paper candidates only)

| Pattern | Where it is drawn | Timing |
| --- | --- | --- |
| Ascending triangle | continuation, priority 1 | 15m close through the flat high |
| Bull flag | continuation, priority 2; needs a pole | 15m close through the flag high |
| Rectangle | upside breakout only; buying the base is out | 15m close through resistance |
| Falling wedge | pullback inside daily HH/HL, low priority | 15m close through the upper boundary |
| Inverse head and shoulders | **daily or 1h only**, never a 15m pattern | 15m close above the neckline |
| Double bottom | **daily or 1h only**, never a 15m pattern | 15m close through the neckline (the eixo) |

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

`paper_candidate` means an **active** long, the daily filters, the 1h or
daily stop inside 3.0–9.66% and at or under 3×ATR(D), the target floor, the
15m close, the Sao Paulo window, the event locks, the loss lock, the
three-trade cap, and the cost gate all passed on a coarse heuristic. It is
a note for a person. The process does not size a live order and does not
call the exchange. `exit_only` means the label must not open a short and
must not open a new long.

Heuristics miss patterns and mislabel them. If the chart disagrees with the
label, the chart wins, and the trade is still skipped when the gate fails.
