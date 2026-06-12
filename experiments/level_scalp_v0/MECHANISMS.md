# Why would price be sensitive at a specific number? — the mechanism map

The atlas tests level *families*; this doc records the *mechanism* behind each one —
because the mechanism predicts the reaction shape (bounce vs pin vs accelerate-then-snap),
the horizon (your "a minute or 3"), and what data can prove it. Families without a
mechanism are curve-fitting bait; families with one get priority.

Ordered by how *forced* the flow is (forced > mechanical > benchmark > behavioral).

## 1. Forced hedging flow — gamma walls (options strikes with big OI)

**Why:** dealers hedge the gamma of big strike OI. Long-gamma dealers near a strike
buy dips / sell rips → price gets *pinned* to the strike (mean reversion at and around
it). Short-gamma flips it (acceleration away). Strongest into expiry (0DTE afternoon),
proportional to OI × gamma, and it's *price-insensitive* flow — the best kind to fade
against or ride with.
**Predicts:** reversion toward the wall inside ~±0.3% of it; effect grows into the close;
sign depends on net dealer positioning (hard to know — treat walls as symmetric magnets
first). Reaction horizon: minutes — fits the scalp geometry.
**Our data:** ThetaData EOD chains SPX/NDX/RUT/DJX (2015→2026 backfill mid-flight),
prior-day OI ONLY (rule A7), basis-mapped to ES/NQ/RTY/YM.
**Status:** tier 3, blocked on the gex_levels regen. Repo graveyard: gamma as
regime/magnet-race = dead; walls as *touch levels* = the open question (n=26 leak-era).

## 2. The book itself — big resting orders (your idea)

**Why:** a large resting bid at P absorbs sellers; price can't trade through until it's
consumed or pulled. Two sub-mechanisms: (a) pure *absorption* (the wall eats the flow →
bounce), (b) *signaling* (others see the wall and front-run it by a tick → bounce starts
1 tick early; also why walls get spoofed). The flip side is informative too: a wall that
gets *pulled* as price approaches predicts trade-through.
**Predicts:** bounce at/1-tick-in-front-of the wall while it holds; fast trade-through
when it pulls; refill-after-fill (iceberg) = an institution *defending* the price =
strongest version. Horizon: seconds to minutes.
**Our data — two tiers:**
- **MBO (4 indices, 2026 only):** see walls form anywhere in the book *in advance* →
  pre-known levels you could rest a limit at. Tier-3 family, with the circularity
  guards from the review (ts_define, evidence/touch disjointness, offset placebo).
- **MBP-1 at-touch (all 28 symbols, 13 months):** you can't see depth in advance, but
  the moment price arrives at ANY level, the displayed size at best IS the wall. So
  "defending size at touch vs the symbol's normal" becomes a *conditioning feature on
  every touch of every family* — does PDH hold better when 800 contracts are defending
  vs 40? That's now recorded per touch (defend_sz / day-median). This is the cheapest,
  broadest version of your resting-orders idea and it needs no new data.

## 3. Stop clusters — liquidity pools just BEYOND salient prices

**Why:** stops collect just past prior extremes (PDH/PDL, overnight H/L, equal highs,
round numbers) — both stop-losses of shorts above a high and buy-stops of breakout
traders. Mechanism: price pushed into the cluster triggers a *cascade through* the
level, then reverses once the resting stop fuel is exhausted and the aggressors find
no follow-through.
**Predicts:** NOT a clean bounce at the level — an overshoot of 2–8 ticks THROUGH it,
then reversion (the sweep-reclaim shape). This is why rule 17 exists (stops must clear
the level; 43% of winners retest the extreme first). Sensitivity lives *past* the
number, not at it.
**Our data:** every tier-1 extreme family; the atlas's approach-speed + MFE/MAE grid
distinguishes bounce-at vs sweep-through-then-revert shapes.
**Status:** tier 1 (this is the Mira lineage — the honest ungated version was negative
at 1–3R structural geometry; never tested at scalp geometry).

## 4. Benchmark execution flow — VWAP and value

**Why:** institutional algos are benchmarked to VWAP; below VWAP they're "ahead" and buy
more / above they slow down. That's systematic, recurring, price-anchored flow → price
reverts toward VWAP intraday; ±2σ stretches snap back. Volume-profile nodes are the
longer-memory version: HVN = price where two-sided business was done before (acceptance
→ reversion within it), LVN = rejected prices (fast traverse — the *through*-move, not
the bounce), POC = the magnet.
**Predicts:** reversion at VWAP bands (minutes), pinning near POC, acceleration across
LVNs. Note LVNs predict the opposite trade from everything else in this doc.
**Our data:** 1m bars (VWAP/profile construction) + MBP-1 pricing, multi-year.
**Status:** tier 2, primary cells #7/#8 — builders are the next increment.

## 5. Inventory anchors — prior close, settlement, gaps

**Why:** overnight positioning is squared against yesterday's close/settlement; a gap
open leaves inventory "wrong" → gap-fill flow toward pdc. Settlement also anchors
margin/PnL marks.
**Predicts:** pdc acts as a magnet early in the session after a gap; the power table
already shows pdc is the single most-touched non-round family (~830–880 touches/symbol,
half overnight).
**Status:** tier 1 (pdc + gap_pdc), in the power table now.

## 6. Pure anchoring — round numbers

**Why:** limit orders, take-profits and stops cluster at round handles (documented
clustering since the 90s); no information content, just coordination. The weakest
mechanism — but it's free, has the most touches (1,500–2,700/symbol in our window),
and clustering alone has historically been measurable.
**Status:** tier 2, primary cells #5/#6, in the power table now.

## The illiquid/other-asset angle (your point, with one hard caveat)

The wall mechanism (#2) should be STRONGER in thin books — one resting order is a
bigger share of typical flow, and fewer HFTs compete to front-run it. We can test this
broadly: MBP-1 is healthy for ~23 non-index symbols (rates ZT/ZN/ZF/ZB, FX 6E/6J/6B…,
CL/NG/HO/RB, grains ZC/ZS/ZW). Rates are especially interesting: deep books, and the
repo's own prior says *rates sweeps revert* (−0.18..−0.29 sweep-runner) — the natural
wall-fade complex. Metals are OUT (MBP-1 mirror is effectively empty) and non-index MBO
is 1 month only → at-touch walls, not pre-known walls, off-index.

**The caveat — your prop copier breaks the illiquid thesis at execution time:** 1–2
contracts × ~20 copied accounts = 20–40 contracts hitting the SAME price at the same
time. On ES that's noise; on ZF or NG that's a meaningful chunk of the book — you
become the wall, the copies fill at different prices, and the backtest's 1-lot fill is
fantasy at fleet size. So: off-index symbols stay in the atlas as *exploratory* cells
(no gating authority), each tagged with a capacity number (typical defending size and
trade rate), and anything that survives gets re-checked at 20–40-lot fleet size in the
Phase 1 queue model before it's allowed to matter.

## What this changes in the build (now in PLAN)

1. Every touch records **defending-side displayed size** (raw + vs day median) — the
   universal at-touch wall feature (#2b). In the detector as of 2026-06-11.
2. **Exploratory symbol sweep** over healthy-MBP-1 non-index symbols for the top
   mechanism families — exploratory only, capacity-tagged.
3. Phase 1/3 carry the **fleet-size fill check** (queue model evaluated at total copied
   size, not 1 lot).
