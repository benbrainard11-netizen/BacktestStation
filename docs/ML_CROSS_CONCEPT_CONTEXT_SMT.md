# SMT cross-concept context build

_Generated `2026-05-11`._

This is the first unified cross-concept context pass.

Goal:

> Take an SMT snapshot row and add what the rest of the research database already knew before that snapshot timestamp.

This is still not entry/exit logic. It is a bigger ML feature table.

## Build

| item | value |
|---|---:|
| source matrix | `data/ml/anchors/smt_previous_day_snapshots.parquet` |
| output matrix | `data/ml/anchors/smt_previous_day_snapshots_xctx.parquet` |
| rows | 4,676 |
| columns | 902 |
| new `xctx.*` columns | 592 |
| context output | `data/ml/context/smt_previous_day_cross_concept_context.parquet` |
| audit | 0 issues, 0 warnings |

Context windows:

- 1h
- 4h
- 24h
- 7d

Context concepts:

- FVG
- sweep
- displacement
- OB
- PSP
- swing pivots
- equal levels
- first-third range
- ORB
- time profile
- volume profile

The anchor concept itself, SMT, is excluded from the context so period-close SMT rows do not count their own SMT event.

## No-Look-Ahead Rule

Every context event is converted to a detector knowable timestamp.

An event can be counted only if:

```text
context_event_knowable_ts < anchor_feature_cutoff_ts
```

That means:

- `at_fire` rows only see context known before SMT fire.
- `at_period_close` rows can see context known by period close.
- future labels are still stored only under `label.*`.
- generated context features live under `xctx.*`.

The snapshot audit passed with 0 issues and 0 warnings:

`docs/ML_SNAPSHOT_AUDIT_SMT_PREV_DAY_XCTX.md`

## Fixed-Split Result

The cross-context matrix was evaluated with the same snapshot leaderboard runner.

Best cross-context fixed-split row:

| snapshot | side | label | test AUC | top 10% rate |
|---|---|---|---:|---:|
| `at_period_close` | low | `label.n1_primary_took_period_n_low` | 0.941 | 100.0% |

Important comparison:

| slice | old best AUC | xctx best AUC | reading |
|---|---:|---:|---|
| `at_fire` | 0.580 | 0.594 | no meaningful gain yet |
| `at_period_close` | 0.910 | 0.941 | meaningful gain |

Row-by-row:

- 36 of 60 fixed-split rows improved.
- 24 of 60 declined.
- `at_period_close` mean AUC delta: +0.019.
- `at_fire` mean AUC delta: -0.014.

Plain English:

The first xctx build helps when the model is allowed to know what happened between SMT fire and period close. It does not yet make raw at-fire SMT much stronger.

## Walk-Forward Result

Walk-forward was rerun over 2020-2025 using top period-close cross-context candidates.

Best walk-forward row:

| snapshot | side | label | mean AUC | min AUC | mean top 10% rate |
|---|---|---|---:|---:|---:|
| `at_period_close` | high | `label.n1_thesis_confirmed_strict` | 0.948 | 0.927 | 100.0% |

Apples-to-apples comparison versus the old SMT walk-forward:

| row | old mean AUC | xctx mean AUC | old min AUC | xctx min AUC |
|---|---:|---:|---:|---:|
| high / `label.n1_thesis_confirmed_strict` | 0.929 | 0.948 | 0.899 | 0.927 |
| all / `label.n1_thesis_confirmed_strict` | 0.912 | 0.939 | 0.875 | 0.922 |
| all / `label.n1_close_moved_with_thesis` | 0.910 | 0.937 | 0.881 | 0.921 |
| low / `label.n1_primary_took_period_n_low` | 0.891 | 0.940 | 0.789 | 0.909 |

This is the strongest evidence from this pass:

> Cross-concept context improves the period-close SMT model, and the improvement holds across walk-forward years.

## Feature Themes

Top feature importance often included:

- recent bearish displacement counts
- recent bearish/bullish FVG counts
- time since recent sweep
- existing period-close aligned FVG/disp/sweep features

Examples from top rows:

- `xctx.n_disp_side_bearish_24h`
- `xctx.n_fvg_side_bearish_24h`
- `xctx.n_fvg_side_bullish_24h`
- `xctx.minutes_since_last_sweep_side_low_24h`
- `pc.n_1h_disp_bearish_same_primary_in_window`
- `pc.minutes_since_last_1h_fvg_bullish_same_primary_in_window`

This matches the original research intuition:

> SMT is strongest when other concepts confirm or describe the surrounding context.

## What This Means

The unified-database direction is validated for one anchor family.

The win is not just "more columns." The useful columns are concept-history columns:

- what recently happened
- which concept family fired
- which side it fired on
- how recently it fired
- whether it was same primary symbol

## Limitations

At-fire SMT did not improve much. That means the current xctx features are not enough to make raw SMT fire-time prediction strong.

Likely missing at-fire features:

- price distance from nearby FVG/OB/VP levels
- nearest equal high/low distance
- active profile location at fire
- richer same-symbol sequencing features
- forward-looking composites must remain labels, not features

## Next

Scale this same xctx builder to the strongest non-SMT anchors:

1. FVG
2. sweep
3. OB
4. time profile
5. volume profile

Then compare each xctx matrix against its standalone leaderboard.
