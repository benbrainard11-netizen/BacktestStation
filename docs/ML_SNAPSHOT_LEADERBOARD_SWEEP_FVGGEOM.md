# ML snapshot leaderboard

_Generated `2026-05-14T08:44:01.050635+00:00`._

## Setup

- Matrix: `data\ml\anchors\sweep_snapshots_xctx_fvggeom.parquet`
- Schema: `data\ml\anchors\sweep_snapshots_xctx_fvggeom.schema.json`
- Event type: `all`
- Snapshots: `at_fire`
- Sides: `low, high, all`
- Labels searched: `15` binary labels
- Top bucket: `10%` of test rows
- Split: train <= 2022 / val = 2023 / test >= 2024
- Full results: `data\ml\anchors\sweep_snapshot_leaderboard_xctx_fvggeom.csv`
- Full parquet: `data\ml\anchors\sweep_snapshot_leaderboard_xctx_fvggeom.parquet`

## Coverage

| item | value |
|---|---:|
| schema_rows | 52,946 |
| schema_feature_columns | 1,305 |
| schema_label_columns | 95 |
| grid_attempts | 45 |
| trained_ok | 45 |
| skipped | 0 |

## Top Models

| snapshot | side | label | test_n | base_rate | test_auc | top_n | top_rate | top_lift |
|---|---|---|---:|---:|---:|---:|---:|---:|
| at_fire | low | `label.ob_confirmation.did_confirm` | 4,646 | 96.7% | 0.894 | 465 | 100.0% | 3.3% |
| at_fire | all | `label.ob_confirmation.did_confirm` | 10,146 | 96.8% | 0.875 | 1,015 | 99.7% | 2.9% |
| at_fire | high | `label.ob_confirmation.did_confirm` | 5,500 | 96.9% | 0.852 | 550 | 100.0% | 3.1% |
| at_fire | low | `label.swept_level_recovery.level_recovered` | 4,646 | 78.2% | 0.793 | 465 | 96.1% | 18.0% |
| at_fire | high | `label.swept_level_recovery.level_recovered` | 5,500 | 66.7% | 0.792 | 550 | 92.2% | 25.4% |
| at_fire | all | `label.swept_level_recovery.level_recovered` | 10,146 | 72.0% | 0.790 | 1,015 | 95.0% | 23.0% |
| at_fire | all | `label.manipulation_range_reaction.took_manipulation_high` | 10,146 | 92.6% | 0.737 | 1,015 | 96.6% | 4.0% |
| at_fire | all | `label.manipulation_range_reaction.one_sided_took_manipulation_low` | 10,146 | 7.4% | 0.731 | 1,015 | 24.3% | 17.0% |

## Best Model Top Features

For `at_fire/low/label.ob_confirmation.did_confirm`, the highest-gain features were:

| feature | gain |
|---|---:|
| `sweep.day_of_week` | 6,220 |
| `sweep.ctx.day_of_week_et` | 3,870 |
| `sweep.ed.tracking_timeframe_1h` | 2,085 |
| `sweep.event_type_pdl_4h` | 741 |
| `xctx.n_fvg_7d` | 604 |
| `xctx.minutes_since_last_smt_side_high_7d` | 587 |
| `fvggeom.age_min_any_symbol_bullish_tapped_below` | 548 |
| `xctx.n_ob_side_bullish_7d` | 491 |
| `xctx.n_swing_7d` | 468 |
| `xctx.minutes_since_last_ogap_side_gap_down_7d` | 423 |

## Interpretation

- The strongest sweep result is order-block confirmation after the sweep, especially low-side sweeps.
- Recovery back through the swept level is also useful and has larger top-bucket lift than the already-high OB confirmation label.
- Prefer `docs\ML_SNAPSHOT_WALK_FORWARD_SWEEP_FVGGEOM.md` for robustness across years.
