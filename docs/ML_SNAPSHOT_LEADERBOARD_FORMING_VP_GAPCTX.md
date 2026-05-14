# ML snapshot leaderboard

_Generated `2026-05-14T08:53:26.072617+00:00`._

## Setup

- Matrix: `data\ml\anchors\forming_vp_snapshots_xctx_gapctx.parquet`
- Schema: `data\ml\anchors\forming_vp_snapshots_xctx_gapctx.schema.json`
- Event type: `all`
- Snapshots: `at_fire`
- Sides: `balanced, buying, selling, all`
- Labels searched: `14` binary labels
- Top bucket: `10%` of test rows
- Split: train <= 2022 / val = 2023 / test >= 2024
- Full results: `data\ml\anchors\forming_vp_snapshot_leaderboard_gapctx.csv`
- Full parquet: `data\ml\anchors\forming_vp_snapshot_leaderboard_gapctx.parquet`

## Coverage

| item | value |
|---|---:|
| schema_rows | 43,150 |
| schema_feature_columns | 1,067 |
| schema_label_columns | 507 |
| grid_attempts | 56 |
| trained_ok | 54 |
| skipped | 2 |

## Top Models

| snapshot | side | label | test_n | base_rate | test_auc | top_n | top_rate | top_lift |
|---|---|---|---:|---:|---:|---:|---:|---:|
| at_fire | balanced | `label.rest_of_day.range_expanded_1x_profile_so_far` | 4,678 | 74.2% | 0.962 | 468 | 100.0% | 25.8% |
| at_fire | all | `label.rest_of_day.range_expanded_1x_profile_so_far` | 8,130 | 71.8% | 0.960 | 813 | 99.9% | 28.1% |
| at_fire | selling | `label.rest_of_day.range_expanded_1x_profile_so_far` | 1,418 | 69.0% | 0.955 | 142 | 100.0% | 31.0% |
| at_fire | buying | `label.rest_of_day.range_expanded_1x_profile_so_far` | 2,034 | 68.0% | 0.944 | 204 | 100.0% | 32.0% |
| at_fire | selling | `label.next_60m.took_profile_so_far_high` | 1,418 | 15.7% | 0.910 | 142 | 69.0% | 53.4% |
| at_fire | buying | `label.next_60m.took_profile_so_far_low` | 2,031 | 14.1% | 0.899 | 204 | 69.6% | 55.5% |
| at_fire | all | `label.next_60m.took_profile_so_far_high` | 8,121 | 24.9% | 0.890 | 813 | 81.2% | 56.3% |
| at_fire | balanced | `label.next_60m.took_profile_so_far_high` | 4,672 | 24.3% | 0.885 | 468 | 83.3% | 59.1% |

## Best Model Top Features

For `at_fire/balanced/label.rest_of_day.range_expanded_1x_profile_so_far`, the highest-gain features were:

| feature | gain |
|---|---:|
| `ts.hour_of_day_utc` | 84,601 |
| `fvp.ed.n_bars` | 23,654 |
| `fvp.hour_of_day_utc` | 15,105 |
| `xctx.n_itr_4h` | 7,943 |
| `xctx.has_itr_1h` | 3,460 |
| `xctx.minutes_since_last_itr_24h` | 3,336 |
| `fvp.ed.vwap_sd` | 3,313 |
| `xctx.has_itr_same_primary_1h` | 3,137 |
| `fvp.ed.profile_range_pts` | 2,845 |
| `fvp.ed.value_area_range_pts` | 2,098 |

## Interpretation

- Adding NDOG/NWOG memory gives a small static leaderboard gain versus base forming-VP xctx.
- Walk-forward did not improve versus the base xctx run, so gap context is useful context but not yet a decisive forming-VP upgrade.
- Prefer `docs\ML_SNAPSHOT_WALK_FORWARD_FORMING_VP_GAPCTX.md` for robustness across years.
