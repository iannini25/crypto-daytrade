# Day-trade playbook

Spot, long only, on a Brazil Bybit Standard Account. The account does not
trade perps or margin. The paper book is **19.9 USDT** (about R$100), funded
by a person via Pix. This file is how a person reads a chart. `python -m desk
scan` only labels the same rules. It does not send orders, and it does not
write the ledger unless `LEDGER_WRITER=1`.

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
   Worked case: stop 3.5%, target 7.9% → (7.9 − 0.30) / (3.5 + 0.30) = 2.
5. **Cost versus the stop.** 0.30% has to be at most 10% of the stop
   distance, so the stop is at least **3.0%**. A 1% stop is rejected.
6. **Account size.** The minimum order is 6 USDT on this ~19.9 USDT book.
   Risk on that minimum order, including the 0.30% cost, has to stay within
   3% of equity. The gate prints the band:

   | Stop distance | Band |
   | --- | --- |
   | under 3.0% | rejected, cost rule |
   | 3.0% through about 3.02% | 1% target zone |
   | about 3.02% through about 9.65% (quoted as ~9.66%) | exception, needs justification |
   | above that cap | rejected |

   Exact edges are `(risk × 19.9 / 6) − 0.30` in percent, with risk at 1%
   and at 3%. Do not loosen them to force a trade.
7. **3×ATR(D) is only a ceiling.** If the 1h or daily swing is farther than
   three daily ATRs from the entry, skip. Do not move the stop up to the
   ATR line to make it fit.
8. **One loss ends the day.** After one losing close on the America/Sao_Paulo
   date, no new entries that day. One open position. No new risk at or
   below 90% of starting equity.

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

The names below are the 15m timing labels. In every case the stop is the
1h or daily swing, the filters above still apply, and a measured move that
does not clear net R:R of 2 is a skip. Do not slide the stop and do not
invent a farther target to pass the gate.

### Ascending triangle

Flat highs, rising lows, inside the daily uptrend. The 15m close through
the flat high is the timing. Invalid if a later 15m close loses the
breakout level, or the daily HH/HL or SMA100 filter breaks.

### Bull flag

A sharp impulse, then a short pause that holds above a 50% retrace of the
pole. Timing is the 15m close through the flag high. Invalid if the pause
gives back more than half the pole, or the daily filter is gone.

### Rectangle breakout

Horizontal support and resistance, at least two touches each side. This
desk only buys the upside, on a 15m close. Invalid on a close back inside
the box. A 1R measured move will not clear the 0.30% cost model.

### Double bottom

Two lows at nearly the same price. The entry is not the second touch. It
is a 15m close through the neckline (the high between the lows). The two
lows should be within a few tenths of a percent. A double bottom against a
daily downtrend, or under SMA100, is not this playbook.

### Inverse head and shoulders

Three lows, the middle one the lowest, shoulders in the same area. Timing
is the 15m close above the neckline. Shoulders that are far apart in price
are not this pattern.

### Falling wedge and cup

Falling wedge: highs and lows descend and the range contracts. Timing is
the 15m close through the upper boundary, not a guess while it is still
falling.

Cup: price leaves a rim, rounds a trough in the middle, and returns to a
similar rim. Timing is the close through the rim. A "V" with the low on
the edge of the window is not a cup.

Both still need daily HH/HL and a close above SMA100.

## What the scanner is allowed to say

`python -m desk scan` can print `ignore`, `watch`, or `paper_candidate`.

`paper_candidate` means the daily filters, the 1h or daily stop, the ATR
ceiling, the 15m close, the Sao Paulo window, the event locks, the loss
lock, and the cost gate all passed on a coarse heuristic. It is a note for
a person. The process does not size a live order and does not call the
exchange.

Heuristics miss patterns and mislabel them. If the chart disagrees with the
label, the chart wins, and the trade is still skipped when the gate fails.
