# ML snapshot leaderboard - sweep FVG+OB geometry

_Generated `2026-05-14`._

## Setup

- Matrix: `data/ml/anchors/sweep_snapshots_xctx_fvggeom_obgeom.parquet`
- Schema: `data/ml/anchors/sweep_snapshots_xctx_fvggeom_obgeom.schema.json`
- Snapshot: `at_fire`
- Sides: `low`, `high`, `all`
- Labels searched: `15`
- Result files:
  - `data/ml/anchors/sweep_snapshot_leaderboard_xctx_fvggeom_obgeom.csv`
  - `data/ml/anchors/sweep_snapshot_leaderboard_xctx_fvggeom_obgeom.parquet`

## Top Models

| side | label | test_n | base_rate | AUC | top_10pct_rate | top_lift |
|---|---|---:|---:|---:|---:|---:|
| low | `label.ob_confirmation.did_confirm` | 4,646 | 96.7% | 0.893 | 100.0% | 3.3% |
| all | `label.ob_confirmation.did_confirm` | 10,146 | 96.8% | 0.870 | 99.7% | 2.9% |
| high | `label.ob_confirmation.did_confirm` | 5,500 | 96.9% | 0.835 | 99.5% | 2.5% |
| all | `label.swept_level_recovery.level_recovered` | 10,146 | 72.0% | 0.799 | 94.8% | 22.8% |
| high | `label.swept_level_recovery.level_recovered` | 5,500 | 66.7% | 0.794 | 92.9% | 26.2% |
| low | `label.swept_level_recovery.level_recovered` | 4,646 | 78.2% | 0.790 | 95.5% | 17.3% |

## Main Deltas Vs FVG Geometry Only

| side | label | old_auc | new_auc | delta |
|---|---|---:|---:|---:|
| high | `label.forward_continuation.continued` | 0.681 | 0.717 | +0.035 |
| high | `label.swept_reference_reaction.wicked_above_ref_closed_below_ref` | 0.509 | 0.538 | +0.029 |
| high | `label.manipulation_range_reaction.one_sided_took_manipulation_low` | 0.681 | 0.708 | +0.027 |
| high | `label.swept_reference_reaction.close_above_reference` | 0.537 | 0.558 | +0.021 |
| all | `label.swept_level_recovery.level_recovered` | 0.790 | 0.799 | +0.009 |

## Interpretation

OB geometry gives the model extra context, but it is not a giant upgrade across every label.

The best use is for harder labels where the model needs context about whether nearby OBs are fresh, already used, or invalidated. The weakest use is the already-high-base-rate OB-confirmation label, where there is little room to improve.
