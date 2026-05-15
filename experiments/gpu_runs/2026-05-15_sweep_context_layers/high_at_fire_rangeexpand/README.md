# GPU XGBoost run — sweep context-layers

_Generated `2026-05-15T03:38:04.043930+00:00`._

## Setup

- matrix: `D:\BacktestStationData\strategy_lab_core_2026_05_14_context_layers\data\ml\anchors\sweep_snapshots_xctx_fvggeom_obgeom_liqgeom_regime.parquet`
- schema: `D:\BacktestStationData\strategy_lab_core_2026_05_14_context_layers\data\ml\anchors\sweep_snapshots_xctx_fvggeom_obgeom_liqgeom_regime.schema.json`
- label: `label.manipulation_range_reaction.range_expanded_2x_manipulation`
- side: `high`
- snapshot: `at_fire`
- event_type: `all`
- device_resolved: `cuda`
- xgboost_version: `3.2.0`
- cuda_available: `True`
- seed: `20260510`
- git_sha: `282e98d4fc02374ce20da58e59f1230a5ee10cf8`

## Per-fold metrics

| test_year | n_train | n_test | base_rate | auc_train | auc_val | auc_test | top_n | top_rate | top_lift | best_iter |
|---|---|---|---|---|---|---|---|---|---|---|
| 2020 | 10378 | 2624 | 0.984 | 0.961 | 0.824 | 0.823 | 263 | 1.000 | +0.016 | 114 |
| 2021 | 13094 | 2755 | 0.972 | 0.989 | 0.830 | 0.909 | 276 | 1.000 | +0.028 | 214 |
| 2022 | 15718 | 2337 | 0.969 | 0.973 | 0.921 | 0.900 | 234 | 1.000 | +0.031 | 128 |
| 2023 | 18473 | 2624 | 0.961 | 0.994 | 0.920 | 0.927 | 263 | 1.000 | +0.039 | 289 |
| 2024 | 20810 | 2635 | 0.974 | 0.982 | 0.940 | 0.941 | 264 | 1.000 | +0.026 | 172 |
| 2025 | 23434 | 2589 | 0.963 | 0.998 | 0.949 | 0.900 | 259 | 1.000 | +0.037 | 477 |

**Mean test AUC across folds:** `0.900`  
**Min-fold test AUC:** `0.823`

## Top mean-gain features (across folds)

| rank | feature | mean_gain |
|---|---|---|
| 1 | `xctx.minutes_since_last_tp_same_primary_24h` | 392.6 |
| 2 | `xctx.minutes_since_last_tp_24h` | 181.9 |
| 3 | `xctx.minutes_since_last_ogap_24h` | 171.2 |
| 4 | `regime.minutes_since_last_same_primary_london_itr` | 126.1 |
| 5 | `fvggeom.has_same_primary_bearish_untouched_below` | 116.6 |
| 6 | `regime.minutes_since_last_any_symbol_london_itr` | 112.6 |
| 7 | `xctx.minutes_since_last_ogap_7d` | 107.7 |
| 8 | `xctx.n_macro_side_high_24h` | 56.0 |
| 9 | `regime.minutes_since_last_same_primary_weekly_itr` | 53.0 |
| 10 | `sweep.day_of_week` | 40.7 |
| 11 | `xctx.minutes_since_last_fvg_same_primary_4h` | 37.9 |
| 12 | `xctx.has_fvp_side_balanced_1h` | 35.6 |
| 13 | `xctx.n_disp_side_bullish_1h` | 35.6 |
| 14 | `regime.minutes_since_last_any_symbol_ny_itr` | 35.4 |
| 15 | `liqgeom.n_eql_any_symbol_any_side_close_taken_within_100pts` | 35.0 |
| 16 | `regime.minutes_since_last_same_primary_ny_itr` | 34.7 |
| 17 | `xctx.minutes_since_last_ogap_side_gap_down_7d` | 33.9 |
| 18 | `fvggeom.distance_pts_any_symbol_bearish_untouched_below` | 32.7 |
| 19 | `regime.minutes_since_last_same_primary_daily_itr` | 32.5 |
| 20 | `regime.minutes_since_last_any_symbol_weekly_itr` | 32.5 |
| 21 | `fvggeom.width_pts_any_symbol_bearish_closed_through_inside` | 31.5 |
| 22 | `fvggeom.age_min_same_primary_bearish_untouched_below` | 31.5 |
| 23 | `liqgeom.n_members_eql_any_symbol_high_wick_taken_above` | 30.3 |
| 24 | `xctx.minutes_since_last_fvg_same_primary_7d` | 30.2 |
| 25 | `liqgeom.n_eql_same_primary_low_close_taken_within_10pts` | 29.9 |

## Interpretation

Compare the mean test AUC to the CPU LightGBM baseline reported in `docs/ML_CONTEXT_LAYER_RESULTS.md` for the same matrix/label/side/snapshot. The two runners share encoding (`pd.get_dummies(dummy_na=True)`), split rules (`train ≤ test_year-2 / val = test_year-1 / test = test_year`), and hyperparameter shape, so the delta isolates device + library.