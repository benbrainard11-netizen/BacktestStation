# ML snapshot leaderboard

_Generated `2026-05-14T08:48:08.487302+00:00`._

## Setup

- Matrix: `data\ml\anchors\forming_vp_snapshots_xctx.parquet`
- Schema: `data\ml\anchors\forming_vp_snapshots_xctx.schema.json`
- Event type: `all`
- Snapshots: `at_fire`
- Sides: `balanced, buying, selling, all`
- Labels searched: `14` binary labels
- Top bucket: `10%` of test rows
- Split: train <= 2022 / val = 2023 / test >= 2024
- Full results: `data\ml\anchors\forming_vp_snapshot_leaderboard_xctx.csv`
- Full parquet: `data\ml\anchors\forming_vp_snapshot_leaderboard_xctx.parquet`

## Coverage

| item | value |
|---|---:|
| schema_rows | 43,150 |
| schema_feature_columns | 869 |
| schema_label_columns | 507 |
| grid_attempts | 56 |
| trained_ok | 54 |
| skipped | 2 |

## Top Models

| snapshot | side | label | test_n | base_rate | test_auc | top_n | top_rate | top_lift |
|---|---|---|---:|---:|---:|---:|---:|---:|
| at_fire | balanced | `label.rest_of_day.range_expanded_1x_profile_so_far` | 4,678 | 74.2% | 0.960 | 468 | 100.0% | 25.8% |
| at_fire | all | `label.rest_of_day.range_expanded_1x_profile_so_far` | 8,130 | 71.8% | 0.959 | 813 | 99.9% | 28.1% |
| at_fire | selling | `label.rest_of_day.range_expanded_1x_profile_so_far` | 1,418 | 69.0% | 0.956 | 142 | 100.0% | 31.0% |
| at_fire | buying | `label.rest_of_day.range_expanded_1x_profile_so_far` | 2,034 | 68.0% | 0.945 | 204 | 100.0% | 32.0% |
| at_fire | selling | `label.next_60m.took_profile_so_far_high` | 1,418 | 15.7% | 0.914 | 142 | 72.5% | 56.9% |
| at_fire | buying | `label.next_60m.took_profile_so_far_low` | 2,031 | 14.1% | 0.897 | 204 | 70.1% | 56.0% |
| at_fire | all | `label.next_60m.took_profile_so_far_high` | 8,121 | 24.9% | 0.890 | 813 | 80.9% | 56.0% |
| at_fire | all | `label.next_60m.took_profile_so_far_low` | 8,121 | 19.5% | 0.875 | 813 | 72.2% | 52.7% |

## Best Model Top Features

For `at_fire/balanced/label.rest_of_day.range_expanded_1x_profile_so_far`, the highest-gain features were:

| feature | gain |
|---|---:|
| `ts.hour_of_day_utc` | 90,168 |
| `fvp.ed.n_bars` | 23,504 |
| `fvp.hour_of_day_utc` | 9,624 |
| `xctx.n_itr_4h` | 8,670 |
| `xctx.has_itr_1h` | 6,597 |
| `xctx.minutes_since_last_itr_24h` | 4,077 |
| `fvp.ed.vwap_sd` | 3,123 |
| `fvp.ed.profile_range_pts` | 2,396 |
| `fvp.ed.poc_volume` | 2,097 |
| `fvp.ed.value_area_range_pts` | 1,971 |

## Interpretation

- Live forming VP is strongest at predicting whether the rest of the day expands beyond the range seen so far.
- The 60-minute high/low-take labels are also learnable and have much larger top-bucket lift because their base rates are lower.
- Prefer `docs\ML_SNAPSHOT_WALK_FORWARD_FORMING_VP_XCTX.md` for robustness across years.
