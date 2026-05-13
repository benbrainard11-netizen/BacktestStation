# ML concept leaderboard summary

_Generated `2026-05-11`._

This compares the current zero-look-ahead snapshot leaderboards across the full concept set.

These are **standalone concept models**, not strategy models. They answer:

> Given only what was knowable when this concept became knowable, can a model rank which events will have a specific future response?

## Current Coverage

| area | status |
|---|---|
| feature matrices | 12 detector feature matrices cataloged |
| research events | 603,127 events cataloged |
| snapshot/model artifacts | 58 anchor/model artifacts cataloged |
| snapshot audits | all generated concept snapshots passed with 0 issues and 0 warnings |
| concepts with baseline snapshot models | SMT, FVG, sweep, displacement, OB, PSP, swing, equal levels, first-third range, ORB, time profile, volume profile |

SMT has two separate snapshot matrices:

- previous-day SMT
- weekly SMT

## Simple Ranking

| tier | concepts | plain English |
|---|---|---|
| strongest | SMT previous-day, weekly SMT, sweep, OB, volume profile, time profile, FVG | These have clear learnable structure. Keep building around them. |
| useful/mid | first-third range, ORB, displacement, swing pivots, equal levels | These are useful context/feature families, but weaker as standalone anchors. |
| weak right now | PSP | Current binary PSP label is near random. Keep the data, but do not prioritize it until labels/features improve. |

## Headline Results

| concept | best label | side | test rows | base rate | AUC | top 10% rate | note |
|---|---|---:|---:|---:|---:|---:|---|
| SMT previous-day | `label.n1_thesis_confirmed_strict` | high | 277 | 43.3% | 0.910 | 100.0% | Very strong, but smaller sample. |
| SMT weekly | `label.n1_thesis_confirmed_strict` | all | 107 | 46.7% | 0.861 | 81.8% | Strong, but sample is small. |
| FVG | `label.mitigation.fully_filled` | all | 41,532 | 77.7% | 0.773 | 93.8% | Clean large-sample standalone concept. |
| sweep | `label.ob_confirmation.did_confirm` | low | 4,646 | 96.7% | 0.888 | 100.0% | Very rankable, but base rate is already extremely high. |
| displacement | `label.retracement.tapped_open` | bearish | 3,714 | 77.2% | 0.681 | 90.9% | Useful support feature, weaker anchor. |
| order block | `label.level_tags.open.wick_tapped` | all | 8,764 | 95.3% | 0.872 | 100.0% | Strong, but best label is easy/high-base-rate. |
| PSP | `label.majority_reaction.all_rolled` | bullish | 1,891 | 43.4% | 0.514 | 46.3% | Weak/noisy in this label setup. |
| swing pivot | `label.breakout.wick_taken` | all | 14,740 | 69.8% | 0.668 | 85.3% | Mildly useful for ranking future pivot takes. |
| equal levels | `label.take.wick_taken` | low | 4,033 | 77.8% | 0.639 | 88.1% | Some signal for being taken; reversal label is weak. |
| first-third | `label.break_high.wick_breached` | all | 1,986 | 81.2% | 0.724 | 93.0% | Useful for range break/extension labels. |
| ORB | `label.broke_only_low` | all | 6,510 | 21.2% | 0.704 | 43.2% | Good practical label because base rate is not inflated. |
| time profile | `label.next_period.took_parent_high` | all | 3,672 | 56.2% | 0.766 | 84.2% | Strong practical context concept. |
| volume profile | `label.vwap_1sd_low_touch.wicked_above` | buying | 1,803 | 98.2% | 0.961 | 100.0% | Very high AUC, but best label is nearly always true. |

## Practical Targets

Some best-AUC labels are too easy because the base rate is already very high. These are the more useful targets to keep researching:

| concept | practical target | why it matters |
|---|---|---|
| SMT previous-day | `label.n1_thesis_confirmed_strict` | Strong AUC with balanced enough base rate. This is still the best anchor family. |
| weekly SMT | `label.n1_thesis_confirmed_strict` | Same idea as previous-day SMT, but sample is smaller. |
| FVG | `label.mitigation.fully_filled` and `label.mitigation.closed_through` | Large sample and clean behavior: which gaps fill or get closed through. |
| sweep | `label.swept_level_recovery.level_recovered` | Better practical label than OB confirmation because base rate is not absurdly high. |
| order block | `label.level_tags.range_far.wick_tapped` or `label.invalidation.invalidated` | Less inflated than open-tap labels; useful for OB quality ranking. |
| time profile | `label.next_period.took_parent_high` / `label.next_period.took_parent_low` | Clean next-period directional/context target. |
| volume profile | profile touch/close labels with base rates below 85% | VP has very strong structure, but avoid labels that are already 95-98% true. |
| ORB | `label.broke_only_high` / `label.broke_only_low` | Practical because base rate is near 21-23%, and top bucket roughly doubles it. |
| first-third | extension/break labels | Useful range-expansion context. |
| swing/equal levels | wick/close take labels | Useful for liquidity-map context, not top-tier standalone. |

## What Works

SMT works best when treated as an anchor for next-period thesis confirmation.

FVG works because gap size, timeframe, time of day, and regime help rank which gaps fill.

Sweep works, but the easiest label is too easy. Level recovery is the better research target.

Order block data has strong structure, but many OB touch labels are high-base-rate. The useful work is separating easy touches from meaningful invalidation/deeper level behavior.

Time profile works well. Parent-period context is predictive for whether the next period takes the parent high/low.

Volume profile has very strong structure. The warning is that several profile-touch labels are almost always true, so future work should focus on harder VP labels or better horizons.

ORB and first-third range are useful. They do not dominate, but they create solid context around range expansion and one-sided breaks.

## What Does Not Work Yet

PSP is weak in the current baseline. AUC is about 0.51, which is basically random. This does not mean PSP is worthless; it means the current binary label `majority_reaction.all_rolled` is not enough.

Equal-level reversal is weak. Equal levels are better as liquidity targets than reversal predictors right now.

Displacement is not a top standalone anchor. It is better as a confirmation/context feature inside larger composite models.

Swing pivots are moderate. They help map liquidity and future takes, but they are not as strong as SMT/FVG/sweep/OB/VP/TP.

## New Snapshot Matrices Built In This Pass

| matrix | rows | columns | audit |
|---|---:|---:|---|
| `ob_snapshots.parquet` | 46,331 | 296 | 0 issues, 0 warnings |
| `psp_snapshots.parquet` | 15,827 | 96 | 0 issues, 0 warnings |
| `swing_snapshots.parquet` | 76,786 | 78 | 0 issues, 0 warnings |
| `eql_snapshots.parquet` | 60,338 | 89 | 0 issues, 0 warnings |
| `ft_snapshots.parquet` | 10,373 | 89 | 0 issues, 0 warnings |
| `orb_snapshots.parquet` | 34,040 | 90 | 0 issues, 0 warnings |
| `tp_snapshots.parquet` | 19,414 | 82 | 0 issues, 0 warnings |
| `vp_snapshots.parquet` | 36,095 | 128 | 0 issues, 0 warnings |

## Best Next Build

The best next build is not entry/exit logic. It is a bigger training table.

Build a unified concept-context dataset where each anchor can see:

- its own event-time features
- prior SMT/FVG/sweep/OB/displacement context
- time profile and volume profile context
- liquidity-map context from swing/equal levels
- session and range context from ORB/first-third

Priority order:

1. Build cross-concept context features for the strongest anchors: SMT, FVG, sweep, OB, TP, VP.
2. Add walk-forward validation for the practical labels, not just fixed train/test splits.
3. Add harder labels for high-base-rate concepts, especially OB and VP.
4. Keep PSP in the database, but do not spend modeling time on it until the label design improves.
