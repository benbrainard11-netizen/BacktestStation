# GPU XGBoost run — sweep context-layers

_Generated `2026-05-15T03:39:29.716910+00:00`._

## Setup

- matrix: `D:\BacktestStationData\strategy_lab_core_2026_05_14_context_layers\data\ml\anchors\sweep_snapshots_xctx_fvggeom_obgeom_liqgeom_regime.parquet`
- schema: `D:\BacktestStationData\strategy_lab_core_2026_05_14_context_layers\data\ml\anchors\sweep_snapshots_xctx_fvggeom_obgeom_liqgeom_regime.schema.json`
- label: `label.swept_level_recovery.level_recovered`
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
| 2020 | 10378 | 2624 | 0.679 | 0.982 | 0.797 | 0.743 | 263 | 0.943 | +0.263 | 238 |
| 2021 | 13094 | 2755 | 0.655 | 0.978 | 0.766 | 0.798 | 276 | 0.960 | +0.305 | 255 |
| 2022 | 15718 | 2337 | 0.758 | 0.935 | 0.800 | 0.796 | 234 | 0.944 | +0.187 | 106 |
| 2023 | 18473 | 2624 | 0.637 | 0.970 | 0.817 | 0.794 | 263 | 0.951 | +0.314 | 267 |
| 2024 | 20810 | 2635 | 0.656 | 0.929 | 0.799 | 0.820 | 264 | 0.970 | +0.314 | 119 |
| 2025 | 23434 | 2589 | 0.674 | 0.961 | 0.825 | 0.810 | 259 | 0.938 | +0.264 | 251 |

**Mean test AUC across folds:** `0.794`  
**Min-fold test AUC:** `0.743`

## Top mean-gain features (across folds)

| rank | feature | mean_gain |
|---|---|---|
| 1 | `regime.last_close_location_same_primary_daily_itr` | 138.3 |
| 2 | `liqgeom.distance_pts_eql_any_symbol_high_fresh_below` | 117.4 |
| 3 | `xctx.minutes_since_last_itr_same_primary_24h` | 112.4 |
| 4 | `liqgeom.distance_pts_eql_same_primary_high_fresh_above` | 111.8 |
| 5 | `sweep.ed.sweep_depth_pts` | 102.0 |
| 6 | `liqgeom.distance_pts_eql_same_primary_any_side_fresh_above` | 91.7 |
| 7 | `xctx.n_orb_side_bearish_1h` | 79.0 |
| 8 | `xctx.minutes_since_last_itr_side_bullish_24h` | 76.3 |
| 9 | `xctx.minutes_since_last_vp_24h` | 70.9 |
| 10 | `fvggeom.n_same_primary_bullish_untouched_within_50pts` | 65.7 |
| 11 | `liqgeom.distance_pts_eql_any_symbol_high_fresh_above` | 62.6 |
| 12 | `fvggeom.distance_pts_same_primary_any_side_untouched_above` | 55.6 |
| 13 | `fvggeom.n_any_symbol_bullish_untouched_within_50pts` | 54.8 |
| 14 | `liqgeom.distance_pts_eql_any_symbol_low_fresh_above` | 52.5 |
| 15 | `regime.last_is_compression_same_primary_daily_itr` | 51.8 |
| 16 | `liqgeom.n_any_source_same_primary_low_fresh_within_100pts` | 51.6 |
| 17 | `xctx.minutes_since_last_itr_4h` | 50.6 |
| 18 | `xctx.n_fvp_side_buying_1h` | 50.2 |
| 19 | `liqgeom.n_members_eql_any_symbol_high_fresh_below` | 49.6 |
| 20 | `regime.last_true_range_pts_same_primary_ny_itr` | 49.2 |
| 21 | `sweep.ed.tracking_timeframe_1h` | 48.9 |
| 22 | `liqgeom.n_eql_any_symbol_low_horizon_expired_within_100pts` | 47.8 |
| 23 | `sweep.ctx.tracking_timeframe_1h` | 45.6 |
| 24 | `regime.last_range_pts_same_primary_weekly_itr` | 45.5 |
| 25 | `sweep.hour_of_day_utc` | 45.1 |

## Interpretation

Compare the mean test AUC to the CPU LightGBM baseline reported in `docs/ML_CONTEXT_LAYER_RESULTS.md` for the same matrix/label/side/snapshot. The two runners share encoding (`pd.get_dummies(dummy_na=True)`), split rules (`train ≤ test_year-2 / val = test_year-1 / test = test_year`), and hyperparameter shape, so the delta isolates device + library.