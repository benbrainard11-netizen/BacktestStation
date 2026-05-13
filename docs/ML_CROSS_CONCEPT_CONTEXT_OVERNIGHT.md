# Cross-concept context overnight build

_Generated `2026-05-12`._

This build scaled the SMT cross-concept context idea to the strongest non-SMT anchor families.

Goal:

> Build bigger zero-look-ahead ML tables where each anchor can see what the rest of the research database already knew before that anchor timestamp.

This is still feature/database infrastructure, not strategy entry or exit logic.

## Scope

Built `xctx.*` matrices for:

- FVG
- sweep
- order block
- time profile
- volume profile

The earlier SMT xctx build remains documented in:

`docs/ML_CROSS_CONCEPT_CONTEXT_SMT.md`

## Outputs

| anchor | rows | columns | xctx cols | output |
|---|---:|---:|---:|---|
| FVG | 209,339 | 716 | 592 | `data/ml/anchors/fvg_snapshots_xctx.parquet` |
| sweep | 52,946 | 677 | 592 | `data/ml/anchors/sweep_snapshots_xctx.parquet` |
| OB | 46,331 | 888 | 592 | `data/ml/anchors/ob_snapshots_xctx.parquet` |
| TP | 19,414 | 662 | 580 | `data/ml/anchors/tp_snapshots_xctx.parquet` |
| VP | 36,095 | 708 | 580 | `data/ml/anchors/vp_snapshots_xctx.parquet` |

Context windows:

- 1h
- 4h
- 24h
- 7d

Feature families:

- `xctx.has_*`
- `xctx.n_*`
- `xctx.minutes_since_last_*`
- `xctx.active_concepts_*`
- `xctx.total_events_*`
- same-primary-symbol versions
- side-specific versions

## Audit

All generated xctx matrices passed snapshot audit.

| anchor | audit |
|---|---|
| FVG | 0 issues, 0 warnings |
| sweep | 0 issues, 0 warnings |
| OB | 0 issues, 0 warnings |
| TP | 0 issues, 0 warnings |
| VP | 0 issues, 0 warnings |

Audit docs:

- `docs/ML_SNAPSHOT_AUDIT_FVG_XCTX.md`
- `docs/ML_SNAPSHOT_AUDIT_SWEEP_XCTX.md`
- `docs/ML_SNAPSHOT_AUDIT_OB_XCTX.md`
- `docs/ML_SNAPSHOT_AUDIT_TP_XCTX.md`
- `docs/ML_SNAPSHOT_AUDIT_VP_XCTX.md`

## Leaderboard Results

### Headline

| anchor | old best AUC | xctx best AUC | reading |
|---|---:|---:|---|
| FVG | 0.773 | 0.775 | mostly flat |
| sweep | 0.888 | 0.901 | small fixed-split gain, not strong in walk-forward |
| OB | 0.872 | 0.876 | mostly flat; easy high-base labels still dominate |
| TP | 0.766 | 0.782 | useful improvement |
| VP | 0.961 | 0.954 | no broad gain; many VP labels are already too easy |

### FVG

Best row stayed the same:

| label | old AUC | xctx AUC | old top 10% | xctx top 10% |
|---|---:|---:|---:|---:|
| `label.mitigation.fully_filled` | 0.773 | 0.775 | 93.8% | 94.4% |

Summary:

- 10 of 15 rows improved.
- 5 of 15 declined.
- Mean AUC delta: +0.002.

Plain English:

FVG already carries most of what it needs in its own event-time features. Simple recent-event xctx counts do not add much.

### Sweep

Best fixed-split row:

| label | old AUC | xctx AUC | note |
|---|---:|---:|---|
| `label.ob_confirmation.did_confirm` low side | 0.888 | 0.901 | high-base-rate label |

Practical row:

| label | old AUC | xctx AUC |
|---|---:|---:|
| `label.swept_level_recovery.level_recovered` all side | 0.790 | 0.795 |

Summary:

- Fixed split improved slightly.
- Walk-forward was basically flat.

Plain English:

Sweep is already strong. Simple xctx counts do not materially change the research conclusion.

### OB

Best row stayed easy:

| label | old AUC | xctx AUC | base rate |
|---|---:|---:|---:|
| `label.level_tags.open.wick_tapped` all side | 0.872 | 0.876 | 95.3% |

Summary:

- 16 of 39 rows improved.
- 23 of 39 declined.
- Mean AUC delta: -0.008.

Plain English:

OB needs harder labels and level-distance features. Simple recent context counts are not the missing piece.

### Time Profile

Best fixed-split row:

| label | old AUC | xctx AUC | old top 10% | xctx top 10% |
|---|---:|---:|---:|---:|
| `label.next_period.took_parent_high` all side | 0.766 | 0.782 | 84.2% | 89.9% |

Walk-forward comparison, 2020-2025:

| label | old mean AUC | xctx mean AUC | old min AUC | xctx min AUC | reading |
|---|---:|---:|---:|---:|---|
| `label.next_period.took_parent_high` all side | 0.778 | 0.793 | 0.751 | 0.758 | real gain |
| `label.next_period.took_parent_low` all side | 0.754 | 0.768 | 0.730 | 0.740 | real gain |
| bullish `label.next_period.took_parent_high` | 0.648 | 0.695 | 0.621 | 0.654 | strong improvement |
| bullish `label.next_period.thesis_confirmed` | 0.648 | 0.695 | 0.621 | 0.654 | strong improvement |

Plain English:

TP is the clear overnight winner. Parent-period time profile gets better when it can also see recent concept context.

### Volume Profile

Best row stayed high-base-rate:

| label | old AUC | xctx AUC | base rate |
|---|---:|---:|---:|
| buying `label.vwap_1sd_low_touch.wicked_above` | 0.961 | 0.954 | 98.2% |

Summary:

- 58 of 166 matched rows improved.
- 108 of 166 declined.
- Mean AUC delta: -0.004.

Plain English:

VP has strong standalone information. Simple recent-event xctx does not broadly improve it. Future VP work should focus on better/harder labels and distance-to-profile-level features.

## Walk-forward Summary

Walk-forward was run for the useful candidates:

- TP xctx versus TP base
- sweep xctx versus sweep base

Result:

| anchor | conclusion |
|---|---|
| TP | xctx improves mean AUC and min AUC on practical next-period high/low labels |
| sweep | xctx is basically flat versus base |

## Main Conclusion

Cross-concept context is not universally useful as simple counts.

It works best for:

- SMT period-close models
- TP next-period models

It is mostly flat for:

- FVG
- sweep
- OB
- VP

That does not mean context is useless for those anchors. It means the first xctx feature family is too simple for them.

## What Is Missing

The next version should add geometry/context features, not just counts:

- nearest FVG distance in points
- nearest OB distance in points
- nearest equal high/low distance
- distance to VP POC/VAH/VAL/VWAP/bands
- whether anchor price is inside/outside value area
- whether recent context is above or below anchor price
- sequence features: sweep then FVG, FVG then OB, displacement after sweep

## Best Next Build

The next best build is a level-geometry context table.

Start with these anchors:

1. SMT
2. FVG
3. sweep
4. OB
5. TP
6. VP

And add nearest-level features from:

- FVG zones
- OB zones
- equal highs/lows
- swing pivots
- VP levels
- session/prior-day/prior-week sweep levels

This should be more valuable than simply adding more count windows.

## Verification

- Built xctx matrices for FVG, sweep, OB, TP, VP.
- Audited all new xctx matrices: 0 issues, 0 warnings.
- Ran xctx leaderboards for all five anchors.
- Ran TP and sweep walk-forward comparisons.
- Rebuilt dataset catalog.

Catalog now sees:

- 12 feature matrices
- 102 anchor/model artifacts
- 603,127 research events
