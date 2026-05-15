# GPU XGBoost run — sweep context-layers

_Generated `2026-05-15T03:47:35.615057+00:00`._

## Setup

- matrix: `D:\BacktestStationData\strategy_lab_core_2026_05_14_context_layers\data\ml\anchors\sweep_snapshots_xctx_fvggeom_obgeom_liqgeom_regime.parquet`
- schema: `D:\BacktestStationData\strategy_lab_core_2026_05_14_context_layers\data\ml\anchors\sweep_snapshots_xctx_fvggeom_obgeom_liqgeom_regime.schema.json`
- label: `label.swept_reference_reaction.first_bar_down_then_final_up`
- side: `high`
- snapshot: `at_fire`
- event_type: `all`
- device_resolved: `cuda`
- xgboost_version: `3.2.0`
- cuda_available: `True`
- seed: `20260510`
- git_sha: `a4d64c344871342ad1b377eebe2637e7a76345ea`

## Per-fold metrics

| test_year | n_train | n_test | base_rate | auc_train | auc_val | auc_test | top_n | top_rate | top_lift | best_iter |
|---|---|---|---|---|---|---|---|---|---|---|
| 2020 | 10378 | 2624 | 0.111 | 0.943 | 0.840 | 0.826 | 263 | 0.335 | +0.224 | 126 |
| 2021 | 13094 | 2755 | 0.119 | 0.950 | 0.829 | 0.827 | 276 | 0.315 | +0.196 | 144 |
| 2022 | 15718 | 2337 | 0.102 | 0.956 | 0.830 | 0.802 | 234 | 0.282 | +0.180 | 184 |
| 2023 | 18473 | 2624 | 0.105 | 0.928 | 0.807 | 0.834 | 263 | 0.361 | +0.256 | 108 |
| 2024 | 20810 | 2635 | 0.117 | 0.959 | 0.839 | 0.833 | 264 | 0.326 | +0.208 | 231 |
| 2025 | 23434 | 2589 | 0.125 | 0.932 | 0.840 | 0.832 | 259 | 0.398 | +0.273 | 142 |

**Mean test AUC across folds:** `0.826`  
**Min-fold test AUC:** `0.802`

## Top mean-gain features (across folds)

| rank | feature | mean_gain |
|---|---|---|
| 1 | `regime.last_direction_bullish_same_primary_daily_itr` | 134.9 |
| 2 | `regime.last_true_range_pts_same_primary_daily_itr` | 94.7 |
| 3 | `sweep.ed.sweep_depth_pts` | 79.9 |
| 4 | `regime.last_direction_bearish_same_primary_daily_itr` | 73.7 |
| 5 | `xctx.minutes_since_last_ogap_4h` | 72.5 |
| 6 | `regime.last_close_location_same_primary_daily_itr` | 68.7 |
| 7 | `regime.last_range_pts_same_primary_daily_itr` | 65.9 |
| 8 | `xctx.minutes_since_last_vp_side_selling_4h` | 46.7 |
| 9 | `liqgeom.n_swing_same_primary_any_side_fresh_within_50pts` | 45.8 |
| 10 | `liqgeom.n_swing_same_primary_low_wick_taken_within_100pts` | 44.8 |
| 11 | `liqgeom.age_min_eql_same_primary_high_fresh_above` | 44.5 |
| 12 | `xctx.minutes_since_last_ogap_same_primary_4h` | 43.8 |
| 13 | `liqgeom.age_min_any_source_same_primary_low_fresh_above` | 40.9 |
| 14 | `sweep.ctx.tracking_timeframe_1d` | 40.8 |
| 15 | `liqgeom.age_min_swing_same_primary_low_fresh_above` | 40.3 |
| 16 | `regime.last_range_pts_same_primary_weekly_itr` | 40.1 |
| 17 | `xctx.minutes_since_last_itr_side_bearish_7d` | 37.7 |
| 18 | `xctx.minutes_since_last_fvp_24h` | 37.4 |
| 19 | `regime.last_range_pts_same_primary_london_itr` | 36.6 |
| 20 | `xctx.minutes_since_last_itr_same_primary_24h` | 36.2 |
| 21 | `xctx.minutes_since_last_fvp_same_primary_7d` | 36.1 |
| 22 | `fvggeom.age_min_same_primary_any_side_untouched_above` | 35.7 |
| 23 | `xctx.minutes_since_last_itr_same_primary_4h` | 35.5 |
| 24 | `regime.last_range_pts_same_primary_asia_itr` | 35.3 |
| 25 | `fvggeom.n_any_symbol_bullish_fully_filled_within_50pts` | 35.1 |

## Interpretation

Compare the mean test AUC to the CPU LightGBM baseline reported in `docs/ML_CONTEXT_LAYER_RESULTS.md` for the same matrix/label/side/snapshot. The two runners share encoding (`pd.get_dummies(dummy_na=True)`), split rules (`train ≤ test_year-2 / val = test_year-1 / test = test_year`), and hyperparameter shape, so the delta isolates device + library.