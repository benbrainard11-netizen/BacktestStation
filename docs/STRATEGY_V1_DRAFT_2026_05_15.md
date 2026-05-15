# Strategy v1 draft — converting ML signals into trade rules

_Generated 2026-05-15. Draft spec for what an actual deployable strategy would look like for the 4 effective robust signals identified today. **No code yet** — this document is the design surface for the choices that need to be made before any rigorous backtest or live trade._

> **Status: draft.** Every section below has a "open question" subsection that asks you (Ben) to confirm a design choice before we commit to it.

## What the lab found today

By the end of today's session, four effective independent robust signals survived multi-year walk-forward validation:

| Signal | Top-10% precision (mean) | Edge over base rate | 6yr top-10% trades | Symbols where it works |
|---|---:|---:|---:|---|
| **SMT period-close — `n1_thesis_confirmed_strict` / side=high** | 1.000 | +0.59 | 69 | All 3 (NQ, ES, YM) |
| **OGAP gap_down rejection — `next_60m.resistance_rejection_3bar`** | 0.95 | +0.30 | 231 | ES-dominant |
| **OGAP gap_up rejection — `next_60m.support_rejection_3bar`** (mirror) | 0.94 | +0.28 | 286 | (per-symbol TBD) |
| **OGAP strict — `strict.next_60m.partial_touch_rejected` / all** | 0.88 | +0.55 | 515 | (per-symbol TBD) |

Combined: ~75 unique trading opportunities per year per index symbol, ~half consensus / half diversification.

These four signals are what a Strategy v1 would translate.

## Strategy v1 spec — the design surface

A "Strategy" in this lab is a deterministic rule set that consumes events and emits trade decisions. Per [CLAUDE.md](../CLAUDE.md), strategies are dumb — no DB access, no model loading in the engine. The ML score gets baked in as a precomputed feature, OR the strategy lives entirely on the research side (analyst-level) until a signal is mature enough to engineer into the engine.

For v1, **the strategy lives on the research side** (a Python script that backtests against historical bars). Promoting to the engine is a v2 question.

### Section 1: Universe & contracts

**Spec:**
- Symbols: ES.c.0, NQ.c.0, YM.c.0
- Per-symbol activation: SMT signal runs on all 3, OGAP signals run on ES first (others added after per-symbol breakdowns).
- Session: regular trading hours, ET 09:30 – 16:00.

**Open questions:**
- Should we trade YM at all? Its precision is the weakest on `resistance_rejection_3bar` (89% mean, 67% worst year). Could split into "always trade YM at top-5% instead of top-10%" or "skip YM entirely."
- Do we want overnight/Asian session exposure? Current data is RTH-anchored — out of scope for v1.

### Section 2: Signal-specific entry rules

#### 2a. SMT period_close `n1_thesis_confirmed_strict` (side=high)

**Anchor event:** SMT divergence detected at a period close (end-of-RTH typically), with a "high" thesis (next period expected to be a lower high — i.e. bearish reference holds).

**Trade direction:** short.

**Entry trigger:** at signal fire time + N bars, market order.

**Open questions:**
- What time exactly is the "period close" for this signal? End of day? End of session? Need to check what the matrix actually anchored on.
- "At signal fire + N bars" — is N = 0 (immediate)? 1 (next bar to confirm)? Wait-for-pullback?
- Real-life mechanic for end-of-day SMT signals: do we enter at close (and hold overnight)? Or wait for next open?

#### 2b. OGAP `resistance_rejection_3bar` (side=gap_down)

**Anchor event:** opening gap_down (today's open < yesterday's close) fires at 09:30 ET on ES (and YM/NQ if we include).

**Trade direction:** short.

**Entry trigger:** the model predicts at gap fire (09:30 ET). The label predicts whether a 3-bar resistance rejection will form in the next 60 min. The natural trade is "short the rip" — wait for price to retest the gap edge / VWAP, then short.

**Open questions:**
- Do we enter at gap fire (09:30) immediately, or wait for the rejection structure to form? The latter has lower slippage risk but might miss fast moves.
- If we wait, what defines "rejection structure forming"? Two consecutive red bars? A failed test of resistance? Need a deterministic trigger.
- What's "resistance"? Yesterday's close? Today's high so far? Both options need defining.

#### 2c. OGAP `support_rejection_3bar` (side=gap_up)

Mirror of 2b. Long, not short. Same open questions.

#### 2d. OGAP strict `partial_touch_rejected@60m` (side=all)

**Anchor event:** any opening gap (up or down).

**Trade direction:** **depends on gap side** — short on gap_up rejection from filled, long on gap_down rejection from filled. The label is direction-agnostic but the trade can't be.

**Open questions:**
- Same as 2b/2c — when exactly does the trade fire?

### Section 3: Stop & target rules

#### Option A — Fixed R-multiple stops

- Stop: 1R = 1 ATR(20) at fire time. Tight enough to keep R-multiples meaningful.
- Target: 2R below entry (for shorts) / above entry (for longs). 2:1 reward-to-risk.
- Time exit: end of session (16:00 ET) or 60 minutes after fire, whichever first.

**Pros:** simple, easy to backtest, R-multiples directly comparable to today's proxy results.
**Cons:** ATR-based stops are coarse; structure-based stops can be tighter.

#### Option B — Structure-based stops

- For OGAP rejection shorts: stop above the resistance level that just rejected.
- For SMT shorts: stop above the period high.
- Targets: at next-down support (VWAP, prior-day low, opposite-side anchor).

**Pros:** more trader-natural, tighter stops on average.
**Cons:** harder to backtest deterministically; "resistance level" needs precise definition.

**Open question:** which option for v1? My take: **Option A** for the first rigorous backtest (deterministic, fast to build), Option B once Option A's edge is confirmed.

### Section 4: Sizing

**Spec:**
- Constant 1 contract per signal per symbol for v1. Don't compound. Don't size by model score.
- Risk: 1R per trade = ATR-defined dollar amount per contract.

**Open questions:**
- Should we scale up when 2+ signals fire on the same date+symbol (consensus trades)?  Half of our trades have consensus — but doubling size on those would skew P&L heavily on a subset.
- Should we size by per-signal precision? SMT (100% precision) trades larger than OGAP strict (88%)?

For v1, **no signal-aware sizing**. Equal weights. Compounding/sizing is a v2 question.

### Section 5: Filters & gates

**Spec for v1 (minimal):**
- Trade only when model score is in top-10% of the signal's prediction distribution that test year.
- Trade only during regular session hours.
- Skip days where signal fires but ATR is unusual (e.g., ATR > 2× 60-day median) — protects against vol-shock days.

**Open questions:**
- Should we require ≥2 signals (consensus filter)? Cuts trade count by ~50% but likely pushes precision higher.
- Should we skip Mondays / Fridays / FOMC / NFP days specifically?
- Should we skip the same symbol on consecutive days if the prior day was a loss?

These are all v2+ questions. For v1, keep it simple.

### Section 6: What counts as a "win"?

The proxy backtest's +1R/−1R framing is synthetic. The rigorous backtest needs to define:

- **Win = target hit before stop.** If target is 2R, win = +2R.
- **Loss = stop hit before target.** Loss = −1R.
- **Time exit before either = some partial outcome.** Either:
  - Treat as 0R (didn't move enough)
  - Treat as P&L = actual close price − entry price (true outcome)
- For **shorts at gap_down rejection**, win = price moves down. Loss = price reclaims resistance.

**Open question:** time exit treatment. My take: use actual close P&L (option 2). It's the honest answer.

### Section 7: Cost model

Default assumptions for v1:
- Commission: $4.50 round-trip per contract (NinjaTrader / Tradovate avg)
- Slippage: 1 tick per side = 2 ticks per round trip = $25 per NQ contract / $12.50 per ES contract
- No financing (intraday)

These need verification against your actual broker pricing.

### Section 8: Performance metrics to report

For the rigorous backtest:

1. **Per-signal:** Sharpe, total R, total $, win rate, avg win $, avg loss $, max DD, max consecutive losses, profit factor
2. **Per-symbol:** all of the above per ES / NQ / YM
3. **Per-year:** all of the above per 2020 → 2025
4. **Portfolio:** combined across signals, with proper time-aware risk-per-day cap (don't blow up if 4 signals fire on the same day)

## Suggested rollout order

1. **Build the rigorous backtest framework** (Option A stop/target, simple v1 rules above). ~4-6 hours of dev work.
2. **Run it for `n1_thesis_confirmed_strict` first** (highest precision, smallest sample). Validate the framework on the cleanest signal.
3. **Run the 3 OGAP signals.** Compare per-signal P&L curves.
4. **Run the combined portfolio.** Tells us "if we deployed all 4 in 2025, what would have happened?"
5. **If portfolio survives**, then start thinking about: paper-trading, contract selection, sizing experiments.

## Open questions summary (for you to answer when you wake up)

1. **YM in or out?** Weak on resistance_rejection. Skip or include with tighter threshold?
2. **Entry timing.** Fire at signal time (09:30 for OGAP)? Or wait for confirmation bar(s)?
3. **Stop/target style.** Fixed R-multiple (Option A) or structure-based (Option B)?
4. **Time-exit P&L treatment.** 0R or actual close-price P&L?
5. **Consensus filter.** Single-signal trades or multi-signal-only?
6. **What's "resistance" for the gap-rejection labels?** Prior close? Today's high? VWAP? Need to pin down.

None of these block forward progress — for any of them I can pick a defensible default and we iterate. But pinning them down now would tighten the rigorous backtest and avoid rework later.

## Reproducing — all today's source data

Everything this draft synthesizes:

- [v1 single-year backtest](ML_BACKTEST_RESISTANCE_REJECTION_V1.md)
- [v2 multi-year walk-forward](ML_BACKTEST_RESISTANCE_REJECTION_V2_WALKFORWARD.md)
- [Label tournament across 10 candidates](ML_LABEL_TOURNAMENT_2026_05_15.md)
- [Portfolio overlap + SMT per-symbol](ML_PORTFOLIO_2026_05_15.md)
- [Label registry](ML_LABEL_REGISTRY.md) (the queryable backing store)
