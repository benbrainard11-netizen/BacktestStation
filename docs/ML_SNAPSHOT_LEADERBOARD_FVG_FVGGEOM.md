# ML snapshot leaderboard

_Generated `2026-05-14T08:37:03.903541+00:00`._

## Setup

- Matrix: `data\ml\anchors\fvg_snapshots_xctx_fvggeom.parquet`
- Schema: `data\ml\anchors\fvg_snapshots_xctx_fvggeom.schema.json`
- Event type: `all`
- Snapshots: `at_fire`
- Sides: `bullish, bearish, all`
- Labels searched: `14` binary labels
- Top bucket: `10%` of test rows
- Split: train <= 2022 / val = 2023 / test >= 2024
- Full results: `data\ml\anchors\fvg_snapshot_leaderboard_xctx_fvggeom.csv`
- Full parquet: `data\ml\anchors\fvg_snapshot_leaderboard_xctx_fvggeom.parquet`

## Coverage

| item | value |
|---|---:|
| schema_rows | 209,339 |
| schema_feature_columns | 1,308 |
| schema_label_columns | 109 |
| grid_attempts | 42 |
| trained_ok | 41 |
| skipped | 1 |

## Top Models

| snapshot | side | label | test_n | base_rate | test_auc | top_n | top_rate | top_lift |
|---|---|---|---:|---:|---:|---:|---:|---:|
| at_fire | all | `label.zone_reaction.took_fvg_high` | 41,537 | 91.9% | 0.891 | 4,154 | 99.9% | 8.0% |
| at_fire | all | `label.zone_reaction.took_fvg_low` | 41,537 | 89.3% | 0.866 | 4,154 | 99.9% | 10.6% |
| at_fire | all | `label.zone_reaction.closed_outside_fvg_range` | 41,537 | 96.2% | 0.757 | 4,154 | 99.6% | 3.4% |
| at_fire | all | `label.zone_reaction.closed_inside_fvg_range` | 41,537 | 3.8% | 0.757 | 4,154 | 13.8% | 10.0% |
| at_fire | bullish | `label.zone_reaction.took_fvg_high_rejected_inside` | 22,791 | 3.6% | 0.751 | 2,280 | 12.2% | 8.6% |
| at_fire | bearish | `label.zone_reaction.took_fvg_low_rejected_inside` | 18,746 | 4.1% | 0.750 | 1,875 | 13.8% | 9.7% |
| at_fire | all | `label.mitigation.fully_filled` | 41,537 | 81.7% | 0.743 | 4,154 | 95.2% | 13.5% |
| at_fire | all | `label.zone_reaction.swept_both_fvg_sides` | 41,537 | 81.2% | 0.738 | 4,154 | 94.4% | 13.2% |

## Best Model Top Features

For `at_fire/all/label.zone_reaction.took_fvg_high`, the highest-gain features were:

| feature | gain |
|---|---:|
| `fvg.side_bearish` | 259,541 |
| `fvg.ed.fvg_width_pts` | 24,685 |
| `ts.hour_of_day_utc` | 20,249 |
| `fvg.side_bullish` | 8,846 |
| `xctx.minutes_since_last_ogap_24h` | 8,349 |
| `xctx.minutes_since_last_tp_24h` | 6,754 |
| `fvg.event_type_15m_fvg` | 4,342 |
| `xctx.n_disp_side_bearish_24h` | 3,781 |
| `ts.day_of_week` | 3,126 |
| `xctx.minutes_since_last_ogap_7d` | 2,667 |

## Interpretation

- The strongest FVG labels are not subtle mitigation labels; they are whether the future window takes the FVG high/low.
- Width, side, hour, and recent opening-gap/time-profile context are doing real work in the best model.
- The one-split leaderboard is only triage. Prefer `docs\ML_SNAPSHOT_WALK_FORWARD_FVG_FVGGEOM.md` for robustness.
