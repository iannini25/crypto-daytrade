# Day-trade playbook

Spot, long only, on a Brazil Bybit Standard Account. The account does not
trade perps or margin. The bankroll for this experiment is about R$100
(about US$20), funded by a person via Pix. This file is how a person reads
a chart. The scanner in `python -m desk scan` only labels the same rules.
It does not send orders.

## Filters that apply to every pattern

1. **Daily structure is higher highs and higher lows.** If the last two
   daily swing highs are not ascending, or the last two daily swing lows
   are not ascending, there is no long. Downtrends and ranges on the daily
   are skipped, even if the 15m chart looks pretty.
2. **Trigger is the 15m chart, and the close confirms.** A wick through
   resistance is not an entry. The 15m candle has to close beyond the level.
3. **Session.** New triggers are for about 10:00–12:30 America/Sao_Paulo.
   Outside that window the same picture is watch-only.
4. **Height.** The box from stop to breakout should be at least about 1%
   of price. Smaller than that, the 0.20% round trip eats the idea. Drop
   to the 1h chart and rebuild the pattern there. Do not force the 15m.
5. **Fees before feelings.** VIP0 spot is 0.10% in and 0.10% out. A flat
   round trip loses 0.20% of notional. Gross R:R of 2 is not enough.

Worked numbers, entry 100, stop 99, target 102:

- Gross reward/risk = 2 / 1 = 2.
- Net risk per unit = (100 − 99) + 0.001 × (100 + 99) = 1.199.
- Net reward per unit = (102 − 100) − 0.001 × (100 + 102) = 1.798.
- R:R after fees ≈ 1.50, which the gate rejects.

The textbook measured move of many patterns is about 1R (target distance
equals the height of the box). That fails this desk on purpose. If the
natural stop and the natural target do not clear **2R after fees**, skip
the trade. Do not slide the stop into the pattern and do not pick a
farther target just to make the ratio pass.

Other hard limits, checked in code by `desk.risk`:

- Risk at the stop, fees included, is at most 1% of equity.
- One open position.
- No new risk when equity is at or below 90% of starting equity.
- Spot category, Buy side, USDT pair.

## Ascending triangle

Flat highs, rising lows, inside a daily uptrend. Supply is being absorbed
at one price while demand steps up.

- Breakout level: the flat high.
- Stop: under the last higher low, not somewhere in the middle of the coil.
- Objective: height of the triangle added to the breakout. If that is under
  2R after fees, skip.
- Invalid: a 15m close back under the rising low, or a daily swing that
  breaks the HH/HL sequence.

## Bull flag

A sharp impulse (the pole), then a short pause that drifts down or sideways
and holds above a 50% retrace of the pole.

- Breakout level: the flag high.
- Stop: under the flag low.
- Objective: pole height projected from the breakout. The flag itself still
  has to be about 1% tall; a hairline flag belongs on the 1h chart.
- Invalid: the pause gives back more than half the pole, or the daily
  filter is gone.

## Rectangle breakout

Horizontal support and resistance with at least two touches on each side.
This desk only buys the upside.

- Breakout level: range high, on a 15m close.
- Stop: under the range low. A stop just under the breakout candle is
  tighter than the pattern and usually fails the fee gate. Skip instead.
- Objective: range height added to the breakout. A 1% box is a 1R measured
  move and will not clear 2R after fees unless the geometry is better than
  the textbook projection. Most rectangles on this desk are skips.
- Invalid: a close back inside the box.

## Double bottom

Two lows at nearly the same price, with a rally between them. The entry is
not the second touch. The entry is a 15m close through the neckline (the
high between the two lows).

- Stop: under the second low.
- Objective: the neckline plus the height from the lows to the neckline.
- The two lows should be within a few tenths of a percent. A much lower
  second low is not a double bottom.
- Needs the daily HH/HL filter like everything else. A double bottom in a
  daily downtrend is someone else's reversal trade.

## Inverse head and shoulders

Three lows. The middle one (the head) is the lowest. The two shoulders are
in the same area. Neckline is the high between the shoulders.

- Entry: 15m close above the neckline.
- Stop: under the right shoulder.
- Objective: neckline plus the distance from the head up to the neckline.
- Shoulders that are far apart in price are not this pattern.

## Falling wedge and cup

Falling wedge: both highs and lows descend, and the range contracts. The
long is the close through the upper boundary, not a guess while it is still
falling. Stop under the most recent low of the wedge. If the box is under
about 1%, move the work to 1h.

Cup: price leaves a rim, rounds out a trough in the middle of the window,
and comes back to a similar rim. Entry is a close through the rim, stop
under the trough. A "V" with the low on the edge of the window is not a cup.

Both still require daily HH/HL. A falling wedge against a daily downtrend
is not this playbook.

## What the scanner is allowed to say

`python -m desk scan` can print `ignore`, `watch`, or `paper_candidate`.

`paper_candidate` means the daily filter, the height, the 15m close, the
Sao Paulo window, and the fee gate all passed on a coarse heuristic. It is
a note for a person. The process does not size a live order, does not write
the paper fill by itself, and does not call the exchange.

Heuristics miss patterns and mislabel them. If the chart disagrees with the
label, the chart wins, and the trade is still skipped when the fee gate
fails.
