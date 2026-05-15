# ML Model Result Index

_Generated `2026-05-15T00:08:19.156960+00:00`._

This file consolidates all saved leaderboard and walk-forward result parquet files.

## Outputs

- CSV: `C:\Users\benbr\BacktestStation\data\ml\catalog\model_result_index.csv`
- Parquet: `C:\Users\benbr\BacktestStation\data\ml\catalog\model_result_index.parquet`
- JSON summary: `C:\Users\benbr\BacktestStation\data\ml\catalog\model_result_index.json`

## Coverage

| Concept | Flavor | Result type | Rows |
|---|---|---|---|
| `disp` | `base` | `leaderboard` | 15 |
| `eql` | `base` | `leaderboard` | 9 |
| `forming_vp` | `gapctx` | `leaderboard` | 56 |
| `forming_vp` | `gapctx` | `walk_forward_summary` | 12 |
| `forming_vp` | `xctx` | `leaderboard` | 56 |
| `forming_vp` | `xctx` | `walk_forward_summary` | 12 |
| `ft` | `base` | `leaderboard` | 42 |
| `fvg` | `base` | `leaderboard` | 15 |
| `fvg` | `fvggeom` | `walk_forward_summary` | 12 |
| `fvg` | `fvggeom_top5` | `walk_forward_summary` | 5 |
| `fvg` | `xctx` | `leaderboard` | 15 |
| `fvg` | `xctx_fvggeom` | `leaderboard` | 42 |
| `fvg` | `xctx_top5` | `walk_forward_summary` | 5 |
| `itr` | `xctx` | `leaderboard` | 42 |
| `itr` | `xctx` | `walk_forward_summary` | 12 |
| `macro` | `xctx` | `leaderboard` | 48 |
| `macro` | `xctx` | `walk_forward_summary` | 10 |
| `macro_event_type` | `base` | `leaderboard` | 432 |
| `macro_event_type` | `summary` | `walk_forward_summary` | 12 |
| `ob` | `base` | `leaderboard` | 39 |
| `ob` | `xctx` | `leaderboard` | 39 |
| `opening_gap` | `xctx_gapctx` | `leaderboard` | 45 |
| `opening_gap` | `xctx_gapctx` | `walk_forward_summary` | 12 |
| `orb` | `base` | `leaderboard` | 45 |
| `psp` | `base` | `leaderboard` | 3 |
| `smt` | `base` | `leaderboard` | 60 |
| `smt` | `summary` | `walk_forward_summary` | 12 |
| `smt_previous_day` | `fvggeom` | `walk_forward_summary` | 18 |
| `smt_previous_day` | `xctx` | `leaderboard` | 60 |
| `smt_previous_day` | `xctx` | `walk_forward_summary` | 8 |
| `smt_previous_day` | `xctx_fvggeom` | `leaderboard` | 60 |
| `smt_weekly` | `base` | `leaderboard` | 60 |
| `sweep` | `base` | `leaderboard` | 9 |
| `sweep` | `base` | `walk_forward_summary` | 6 |
| `sweep` | `fvggeom` | `walk_forward_summary` | 12 |
| `sweep` | `fvggeom_obgeom` | `walk_forward_summary` | 12 |
| `sweep` | `xctx` | `leaderboard` | 9 |
| `sweep` | `xctx` | `walk_forward_summary` | 6 |
| `sweep` | `xctx_fvggeom` | `leaderboard` | 45 |
| `sweep` | `xctx_fvggeom_obgeom` | `leaderboard` | 45 |
| `sweep` | `xctx_top9` | `walk_forward_summary` | 9 |
| `swing` | `base` | `leaderboard` | 6 |
| `tp` | `base` | `leaderboard` | 18 |
| `tp` | `base` | `walk_forward_summary` | 8 |
| `tp` | `fvggeom` | `walk_forward_summary` | 10 |
| `tp` | `xctx` | `leaderboard` | 18 |
| `tp` | `xctx` | `walk_forward_summary` | 8 |
| `tp` | `xctx_fvggeom` | `leaderboard` | 18 |
| `vp` | `base` | `leaderboard` | 180 |
| `vp` | `v2_xctx` | `leaderboard` | 48 |
| `vp` | `v2_xctx` | `walk_forward_summary` | 12 |
| `vp` | `xctx` | `leaderboard` | 180 |

## Highest Static Test AUC Rows

| Concept | Flavor | Snapshot | Side | Label | Test rows | Base rate | AUC | Top bucket |
|---|---|---|---|---|---|---|---|---|
| `macro_event_type` | `base` | `at_fire` | `high` | `label.next_15m.range_expanded_2x_pre_60m` | 144 | 0.167 | 1.000 | 1.000 |
| `macro_event_type` | `base` | `at_fire` | `all` | `label.next_15m.range_expanded_2x_pre_60m` | 144 | 0.167 | 1.000 | 1.000 |
| `macro_event_type` | `base` | `at_fire` | `all` | `label.next_15m.range_expanded_2x_pre_60m` | 180 | 0.072 | 0.993 | 0.722 |
| `macro_event_type` | `base` | `at_fire` | `high` | `label.next_15m.range_expanded_2x_pre_60m` | 180 | 0.072 | 0.991 | 0.722 |
| `smt_previous_day` | `xctx_fvggeom` | `at_period_close` | `high` | `label.n1_primary_took_period_n_high` | 277 | 0.563 | 0.970 | 1.000 |
| `smt_previous_day` | `xctx_fvggeom` | `at_period_close` | `low` | `label.n1_primary_took_period_n_low` | 251 | 0.482 | 0.967 | 1.000 |
| `macro_event_type` | `base` | `at_fire` | `all` | `label.next_5m.range_expanded_2x_pre_15m` | 75 | 0.187 | 0.966 | 0.875 |
| `smt_previous_day` | `xctx_fvggeom` | `at_period_close` | `all` | `label.n1_primary_took_period_n_low` | 528 | 0.456 | 0.964 | 1.000 |
| `macro_event_type` | `base` | `at_fire` | `all` | `label.next_5m.range_expanded_2x_pre_15m` | 180 | 0.072 | 0.963 | 0.611 |
| `forming_vp` | `gapctx` | `at_fire` | `balanced` | `label.rest_of_day.range_expanded_1x_profile_so_far` | 4,678 | 0.742 | 0.962 | 1.000 |
| `smt_previous_day` | `xctx_fvggeom` | `at_period_close` | `all` | `label.n1_primary_took_period_n_high` | 528 | 0.530 | 0.962 | 1.000 |
| `macro_event_type` | `base` | `at_fire` | `high` | `label.next_5m.range_expanded_2x_pre_15m` | 144 | 0.215 | 0.961 | 0.933 |
| `smt_previous_day` | `xctx_fvggeom` | `at_period_close` | `high` | `label.n1_thesis_confirmed_strict` | 277 | 0.433 | 0.961 | 1.000 |
| `smt_previous_day` | `xctx_fvggeom` | `at_period_close` | `high` | `label.n1_primary_took_period_n_low` | 277 | 0.433 | 0.961 | 1.000 |
| `vp` | `base` | `at_fire` | `buying` | `label.vwap_1sd_low_touch.wicked_above` | 1,803 | 0.982 | 0.961 | 1.000 |
| `forming_vp` | `gapctx` | `at_fire` | `all` | `label.rest_of_day.range_expanded_1x_profile_so_far` | 8,130 | 0.718 | 0.960 | 0.999 |
| `forming_vp` | `xctx` | `at_fire` | `balanced` | `label.rest_of_day.range_expanded_1x_profile_so_far` | 4,678 | 0.742 | 0.960 | 1.000 |
| `forming_vp` | `xctx` | `at_fire` | `all` | `label.rest_of_day.range_expanded_1x_profile_so_far` | 8,130 | 0.718 | 0.959 | 0.999 |
| `smt_previous_day` | `xctx_fvggeom` | `at_period_close` | `high` | `label.n1_close_moved_with_thesis` | 277 | 0.437 | 0.958 | 0.964 |
| `forming_vp` | `xctx` | `at_fire` | `selling` | `label.rest_of_day.range_expanded_1x_profile_so_far` | 1,418 | 0.690 | 0.956 | 1.000 |
| `forming_vp` | `gapctx` | `at_fire` | `selling` | `label.rest_of_day.range_expanded_1x_profile_so_far` | 1,418 | 0.690 | 0.955 | 1.000 |
| `smt_previous_day` | `xctx_fvggeom` | `at_period_close` | `low` | `label.n1_close_moved_with_thesis` | 251 | 0.502 | 0.955 | 1.000 |
| `vp` | `xctx` | `at_fire` | `buying` | `label.vwap_1sd_low_touch.wicked_above` | 1,803 | 0.982 | 0.954 | 1.000 |
| `smt_previous_day` | `xctx_fvggeom` | `at_period_close` | `all` | `label.n1_close_moved_with_thesis` | 528 | 0.468 | 0.953 | 1.000 |
| `macro_event_type` | `base` | `at_fire` | `high` | `label.next_15m.range_expanded_2x_pre_60m` | 75 | 0.120 | 0.951 | 0.750 |

## Highest Walk-Forward Mean AUC Rows

| Concept | Flavor | Snapshot | Side | Label | Folds ok | Rows | Mean AUC | Min AUC | Top bucket |
|---|---|---|---|---|---|---|---|---|---|
| `macro_event_type` | `summary` | `at_fire` | `high` | `label.next_5m.range_expanded_2x_pre_15m` | 4 | 423 | 0.966 | 0.953 | 0.859 |
| `macro_event_type` | `summary` | `at_fire` | `all` | `label.next_5m.range_expanded_2x_pre_15m` | 4 | 432 | 0.966 | 0.946 | 0.841 |
| `smt_previous_day` | `fvggeom` | `at_period_close` | `high` | `label.n1_thesis_confirmed_strict` | 6 | 699 | 0.964 | 0.955 | 1.000 |
| `smt_previous_day` | `fvggeom` | `at_period_close` | `low` | `label.n1_thesis_confirmed_strict` | 6 | 650 | 0.959 | 0.946 | 1.000 |
| `smt_previous_day` | `fvggeom` | `at_period_close` | `all` | `label.n1_thesis_confirmed_strict` | 6 | 1,349 | 0.955 | 0.944 | 0.991 |
| `forming_vp` | `gapctx` | `at_fire` | `balanced` | `label.rest_of_day.range_expanded_1x_profile_so_far` | 6 | 12,916 | 0.952 | 0.925 | 0.999 |
| `forming_vp` | `xctx` | `at_fire` | `balanced` | `label.rest_of_day.range_expanded_1x_profile_so_far` | 6 | 12,916 | 0.952 | 0.928 | 1.000 |
| `forming_vp` | `gapctx` | `at_fire` | `all` | `label.rest_of_day.range_expanded_1x_profile_so_far` | 6 | 22,922 | 0.950 | 0.917 | 0.999 |
| `forming_vp` | `xctx` | `at_fire` | `all` | `label.rest_of_day.range_expanded_1x_profile_so_far` | 6 | 22,922 | 0.949 | 0.916 | 0.999 |
| `smt_previous_day` | `xctx` | `at_period_close` | `high` | `label.n1_primary_took_period_n_low` | 6 | 699 | 0.948 | 0.927 | 1.000 |
| `smt_previous_day` | `xctx` | `at_period_close` | `high` | `label.n1_thesis_confirmed_strict` | 6 | 699 | 0.948 | 0.927 | 1.000 |
| `smt_previous_day` | `xctx` | `at_period_close` | `high` | `label.n1_close_moved_with_thesis` | 6 | 699 | 0.945 | 0.923 | 0.987 |
| `forming_vp` | `xctx` | `at_fire` | `buying` | `label.rest_of_day.range_expanded_1x_profile_so_far` | 6 | 5,814 | 0.943 | 0.908 | 0.999 |
| `forming_vp` | `xctx` | `at_fire` | `selling` | `label.rest_of_day.range_expanded_1x_profile_so_far` | 6 | 4,192 | 0.943 | 0.909 | 0.995 |
| `forming_vp` | `gapctx` | `at_fire` | `buying` | `label.rest_of_day.range_expanded_1x_profile_so_far` | 6 | 5,814 | 0.943 | 0.905 | 0.997 |
| `forming_vp` | `gapctx` | `at_fire` | `selling` | `label.rest_of_day.range_expanded_1x_profile_so_far` | 6 | 4,192 | 0.942 | 0.904 | 0.995 |
| `smt_previous_day` | `xctx` | `at_period_close` | `low` | `label.n1_primary_took_period_n_low` | 6 | 650 | 0.940 | 0.909 | 0.987 |
| `smt_previous_day` | `xctx` | `at_period_close` | `all` | `label.n1_thesis_confirmed_strict` | 6 | 1,349 | 0.939 | 0.922 | 1.000 |
| `smt_previous_day` | `xctx` | `at_period_close` | `all` | `label.n1_close_moved_with_thesis` | 6 | 1,349 | 0.937 | 0.921 | 0.984 |
| `smt_previous_day` | `xctx` | `at_period_close` | `all` | `label.n1_primary_took_period_n_low` | 6 | 1,349 | 0.936 | 0.913 | 1.000 |
| `smt_previous_day` | `xctx` | `at_period_close` | `low` | `label.n1_thesis_confirmed_strict` | 6 | 650 | 0.930 | 0.914 | 1.000 |
| `smt` | `summary` | `at_period_close` | `high` | `label.n1_thesis_confirmed_strict` | 6 | 699 | 0.929 | 0.899 | 0.987 |
| `smt` | `summary` | `at_period_close` | `high` | `label.n1_primary_took_period_n_low` | 6 | 699 | 0.929 | 0.899 | 0.987 |
| `smt` | `summary` | `at_period_close` | `high` | `label.n1_close_moved_with_thesis` | 6 | 699 | 0.928 | 0.891 | 0.987 |
| `macro_event_type` | `summary` | `at_fire` | `high` | `label.next_15m.range_expanded_2x_pre_60m` | 2 | 216 | 0.925 | 0.850 | 0.773 |

## Reading The Results

- Static leaderboard rows are useful for fast comparison, but they are easier to overfit.
- Walk-forward rows matter more because each fold tests on later years.
- Very high AUC on labels with very high base rate can still be less useful than a lower-AUC hard label.
- `top_features` is a model diagnostic, not proof of causality.
