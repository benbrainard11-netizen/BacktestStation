# Ben's trading model — formalized from his own words (2026-06-10)

Source: Ben's discretionary framework, dictated for systematization. This is the NORTH-STAR
context doc for entry model v2 features and new trigger families. Update as he adds concepts.

## The core abstraction: FRACTAL CYCLES with three phases
Every timeframe is a cycle (weekly, daily, session). Each cycle has:
1. **Manipulation** — the sweep that forms the cycle's high/low (e.g. Tuesday trades below
   Monday's low = the weekly manipulation). Usually accompanied by a DIVERGENCE (SMT/PSP).
2. **Distribution/continuation** — the directional leg after manipulation completes
   (Wed/Thu trade up from the swept Monday low).
3. (implicit) accumulation/pre-manipulation before it.

**What the current system already does:** trades the manipulation moment itself (sweep +
reclaim + SMT + gate). It is ONE slice of this model — the broadest one.

**What's missing (Ben's edge claims, in testable form):**
- **Cycle-phase context**: every LTF setup should know the state of the HTF cycle above it
  (has the weekly manipulated yet? which direction?). Post-manipulation LTF setups ALIGNED
  with the HTF cycle direction should outperform. -> context features: per-TF cycle phase,
  direction, bars-since-manipulation.
- **Continuation signatures on LTF after HTF manipulation** (new trigger family, not
  reversal-at-sweep): LTF divergences in the HTF direction, **cross-asset FVG fill
  divergence ("SMT fill": one asset fills an FVG, the paired asset doesn't = the
  non-filling asset is strong/weak)**, precision candles at key opens.
- **Strength switch**: relative-strength FLIP events (NQ takes PDH while YM fails to =
  switch). A sequence-level event, not a static feature.

## Worked example (2026-06-09, Ben: "picture perfect")
Swept PDH -> retraced making an FVG + precision candle at the open -> YM filled the FVG,
NQ did NOT (fill divergence) -> also a strength switch (NQ took PDH, YM failed) ->
continued DOWN the rest of the day. [Verifiable against data — candidate calibration day.]

## Evidence so far for the context layer (2026-06-10 ledger splits)
- PDL long reclaims: below weekly open +0.673 vs above +0.124 (n=33/33) — discount matters
  for longs; PDH shorts context-indifferent. prior-week levels: below daily open +1.135
  vs above +0.559. The frozen gate has NO open-relative features -> provably blind to this.
- Family x time: asia levels expire after 10am; open strong, lunch weak, PM tail strong.

## Prior cautions (don't re-learn these)
- SMT-fill (FVG/gap) tested as an ENTRY GATE in mira_upgraded_v0 HURT — but its role here
  is different (continuation signature inside a cycle phase). Test in-role before judging.
- Every concept enters the pipeline: descriptive split -> feature -> challenger A/B -> OOS
  verdict. Nothing ships on narrative alone; champion frozen until beaten everywhere.

## Ben's answers (2026-06-10) — DEFINITIONS, all bar-computable
1. **Cycle timing**: the cycle's high/low usually forms in the FIRST HALF; sometimes waits
   to ~Q3 (late reversal). Candle-profile context matters: if the HTF candle is expected to
   be an inside/choppy range candle, gauging its high/low is much harder (-> expected-profile
   as a context feature). "Failed cycle" is really a FAILED MANIPULATION ATTEMPT: the
   high-probability high/low forms (sweep+divergence), then gets RUN THROUGH. (= exactly our
   stopped-out trades; the cycle then often re-attempts.)
2. **PSP (precision swing point)**: SAME-TIMESTAMP candle on correlated assets closes in
   OPPOSITE directions (Tue NQ closes bearish, YM bullish). One-candle CLOSURE divergence —
   vs SMT which is prior-high/low divergence. **Precision candle** = any same-timestamp
   candle with differing closes. (OHLC-only today; intra-candle/bid-ask versions = open idea.)
3. **SMT fill** (worked example decoded): 15m FVG forms; the 10:15 candle is a precision
   candle (YM bullish close = stronger, NQ bearish = weaker). The STRONGER asset (YM) fills
   the bearish gap / trades above the precision-candle high (the gap's entry level); the
   WEAKER (NQ) does NOT fill / never trades above that high -> continuation in the weak
   direction. SMT fill := same-timestamp gap filled on one asset, not the other. The
   precision-candle high/low acts as the entry/invalidation reference.
4. **Strength switch**: probably continuous relative strength, with extra weight at event
   moments; main use = pick WHICH asset to trade (trade the weak one short / strong one
   long) and spot reversals. Exact formulation = open research.

## Divergence STACKING (Ben 2026-06-10): "double crack in correlation"
- A PDL SMT *plus* a DAILY PSP at the same low = two independent correlation cracks ->
  much stronger signal than either alone. The day's low then gets marked by a 4h SMT/PSP,
  and with HTF aligned you drill to LTF for the entry (the alignment cascade).
- Feature: **crack count** — number of TF-ladder divergences (SMT + PSP, anchored AT THE
  SWEEP/extreme, not at the trigger) co-occurring at one cycle extreme. Test: ledger split
  by stack depth (1 vs 2+). NOTE: PSP-at-trigger tested 2026-06-10 = NOISE (sign flips by
  TF); PSP must be anchored at the sweep candle — the manipulation moment — to be faithful.

## Confirmation rules — FVG & Order Block (Ben 2026-06-14, exact mechanics)
The reclaim/displacement STRUCTURE is breakeven (proven 12yr); the CONFIRMATION is what separates
good sweeps from bad. Two bar-based confirmations (computable on 12yr of candles, NO MBO needed):

**Order Block (for a LONG that swept a low, e.g. PDL):**
1. Sweep candle = the candle whose low took out the level.
2. OB candle = the sweep candle IF it closed DOWN (bearish); ELSE the most recent down-close candle
   before the sweep candle.
3. Confirmation = a later candle CLOSES ABOVE the OB candle's OPEN.
   (Mirror short: swept a high -> OB = up-close candle -> confirm when a candle closes BELOW its open.)
Example: 10:00 15m candle sweeps PDL + closes bearish = the OB; 10:15 closes above the 10:00 open = confirmed.

**FVG (for a LONG):** after the sweep, a bullish FVG forms (3-candle gap: candle1.high < candle3.low)
in the reversal direction; hypothesis = setups where an FVG forms + price respects it are the good ones.

**MULTI-TF + TF-MATCHING (both):** confirmation can show on 1m/5m/15m/30m, and the TF is MATCHED to the
level's TF — deep levels (PDL) confirm on higher-TF FVG/OB (15m), shallow levels (overnight/premarket
low) on lower-TF (1m/5m). Same timeframe-sync logic that worked for SMT ([[upgraded_mira_smt]]).
Two uses: (a) FILTER/feature on existing reclaim trades (does presence separate winners), tested first;
(b) REPLACEMENT entry trigger (enter on OB-confirm/FVG-fill instead of the bare reclaim close) — later.

## Structure-ANCHORED flow (Ben 2026-06-14) — the entry-model frontier
The +0.086 drift edge is TIME-anchored (last 90s before decision) — a blind clock. Better: anchor the
flow reading to the STRUCTURE. When an OB forms and price retraces INTO it, read the order book INSIDE
the OB zone — absorption / iceberg-refill / aggression there predict whether it HOLDS (continuation).
When an FVG forms and price returns to it, read flow AT the fill — does it fill-and-continue or get
rejected / left unfilled. The flow that MATTERS is the flow at the exact price the reaction happens,
not generic last-90s flow. Mechanism-faithful: an OB works because institutions defend it; an FVG
continues because there's real flow there — measuring the book AT that location is how you SEE it.
This might BEAT drift, not just stack. Caveat: 2026-MBO only + zone-formed subset (~5-15%) = small
pilot; if it shows promise, THAT justifies the ~$2k deeper-MBO buy for power. Built: flow_at_zone.py.

## Immediate testables from these definitions (no new data needed)
- PSP detector: aligned 15m/1h bars, close-direction disagreement -> event stream.
- SMT-fill detector: FVG per asset + fill tracking + cross-asset same-timestamp comparison.
- Both -> (a) context features for v2, (b) candidate CONTINUATION trigger family,
  (c) descriptive splits on the existing 612-trade ledger first (cheapest evidence).
