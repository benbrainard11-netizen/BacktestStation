# Phase 2c — key-question diagnostic: NULL on the summary (adversarially verified)

Dated 2026-06-14. Tool: `diag_policy.py` on `out/dataset_ES_trading_day.parquet` (gitignored).
Adversarially verified by a 3-lens panel (leakage auditor, independent economist, path-B skeptic) —
**all three refuted the optimistic "Path A" reading at high confidence (verdicts B / C / C).**

## The question

Phase 2b showed OFI predicts the level *break* (classification) but the naive ±8-tick/30-min trade is
`realized_R` ≤ 0. The 2c question: is that because the signal never reaches a target (path B: labels
insufficient), or because it reaches MFE the naive exit can't keep (path A: fixable wrapper)?

## Answer: neither — it's a NULL after costs, and OFI is a volatility proxy in the trade frame

Honest, ex-ante, ordering-true test — the 1R/1R break-direction race (`y_target_before_stop` is the only
true stop-vs-target ordering label; `realized_R` is capped at ±1), bucketed only on ex-ante `ofi_signed`:

| OFI tercile | n | target-before-stop | gross_R | net_R (after 0.25R cost) |
|---|---|---|---|---|
| low | 1881 | 0.377 | +0.035 | **−0.215** |
| mid | 1773 | 0.315 | +0.150 | **−0.100** |
| high | 1766 | 0.379 | +0.034 | **−0.216** |

- **No ex-ante bucket clears zero after costs** (best is mid at −0.10R; mid's gross is a timeout
  fractional-mark artifact, not an exit).
- **OFI has no directional R-tilt:** corr(OFI, realized_R) = pearson +0.016 / spearman +0.011. The win
  rate of the honest race is **identical** top-vs-bottom (0.379 vs 0.377). corr(|OFI|, excursion range)
  = +0.325 → **OFI magnitude is a volatility/activity proxy, not a money edge.**
- **No asymmetry to harvest:** p(MFE≥1R) ≈ p(MAE≥1R) ≈ 0.53 in the top bucket; median(MFE−MAE)=0,
  frac(MFE>MAE)=0.493 (coin flip). High-OFI events are high-*range* events that blow through both
  barriers symmetrically.

## Errors caught by the panel (recorded so we don't repeat them)

1. **Leaky "drop the hold branch" lever.** The first 2c read proposed dropping the hold branch to rescue
   high-OFI — but `y_hold` is a *post-hoc outcome label*, the same untradeable conditioning as the
   "+0.832R break-only" upper bound. Removing it ex-ante would require a break-vs-hold classifier on weak
   features — the feature expansion 2c forbids. Internally contradictory.
2. **`realized_R` is capped at ±1** (it IS a 1R/1R bracket). "Avg MFE 2.55R is there, the wrapper just
   can't keep it" overreached — that label cannot capture >1R, and the summary can't simulate a wider
   target.
3. **Timeout fractional mark props the headline.** ~76% of high-OFI chop rows carry a fractional MTM
   (not a fill); flooring timeouts to 0R flips high-OFI from +0.034 to ~−0.022 pre-cost.
4. **Geometry sweep un-runnable on the summary.** No tick path / no MFE-vs-MAE ordering; 24–34% of
   top-tercile trades hit both 1R barriers with unknown order. A 2R/1R bracket spans +0.50R (optimistic)
   to −0.21R (conservative) — a 0.72R gap the summary cannot resolve. "Run the sweep on this parquet"
   was impossible.

## Reconciliation with Phase 1 (the classifier still stands)

Phase 1's OFI→break edge is real *as a classifier*: corr(OFI, y_break) = +0.234, resolved-subset
break-rate monotone 0.278/0.371/0.497, AUC 0.639. The panel does not refute that. What 2c establishes is
that **the classification edge does not convert into a standalone tradeable break-direction trade** —
high-OFI resolved break-rate only reaches ~0.50 (coin flip), and on the full tradeable set OFI does not
tilt the 1R/1R race at all. The signal discriminates break-vs-hold (mostly by flagging *holds* at low
OFI), not profitable-vs-unprofitable.

## Verdict and the only legitimate next step

**The naive ±8-tick/30-min OFI break-direction wrapper is NULL after costs.** A documented negative —
and a useful one: it blocks training a model on a wrapper with no demonstrated directional edge.

The geometry/entry sweep cannot be run on the summary. The only honest way to test the remaining
hypotheses (asymmetric geometry; ex-ante **confirmation/reclaim** entry rather than raw-touch entry) is a
**tick-level (MBP-1) honest-bracket re-simulation** with stop-wins-ties fills (CLAUDE.md §8). Priors are
low (OFI shows ~0 directional R-tilt), and this overlaps heavily with existing repo work that already
found edge at reclaim entry (`mira_upgraded_v0/reclaim_entry.py`, `legal_rebuild_edges`). So the open
question is strategic: is the OFI resolver better used as a standalone trade (low prior) or as the
**classifier/conditioner** it was originally specced to be (feeding the existing reclaim edge)?
