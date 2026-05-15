# GPU XGBoost run — sweep context-layers

_Generated `2026-05-15T03:45:31.734656+00:00`._

## Setup

- matrix: `D:\BacktestStationData\strategy_lab_core_2026_05_14_context_layers\data\ml\anchors\sweep_snapshots_xctx_fvggeom_obgeom_liqgeom_regime.parquet`
- schema: `D:\BacktestStationData\strategy_lab_core_2026_05_14_context_layers\data\ml\anchors\sweep_snapshots_xctx_fvggeom_obgeom_liqgeom_regime.schema.json`
- label: `label.ob_confirmation.did_confirm`
- side: `low`
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
| 2020 | 8568 | 2010 | 0.967 | 0.974 | 0.945 | 0.838 | 201 | 1.000 | +0.033 | 168 |
| 2021 | 10545 | 2112 | 0.977 | 0.957 | 0.841 | 0.886 | 212 | 1.000 | +0.023 | 95 |
| 2022 | 12555 | 2505 | 0.973 | 0.958 | 0.898 | 0.847 | 251 | 1.000 | +0.027 | 94 |
| 2023 | 14667 | 2188 | 0.981 | 0.961 | 0.854 | 0.898 | 219 | 1.000 | +0.019 | 100 |
| 2024 | 17172 | 2171 | 0.969 | 0.973 | 0.907 | 0.883 | 218 | 1.000 | +0.031 | 152 |
| 2025 | 19360 | 2168 | 0.970 | 0.964 | 0.886 | 0.929 | 217 | 1.000 | +0.030 | 118 |

**Mean test AUC across folds:** `0.880`  
**Min-fold test AUC:** `0.838`

## Top mean-gain features (across folds)

| rank | feature | mean_gain |
|---|---|---|
| 1 | `sweep.day_of_week` | 184.4 |
| 2 | `sweep.ctx.day_of_week_et` | 103.7 |
| 3 | `sweep.hour_of_day_utc` | 89.0 |
| 4 | `sweep.ed.tracking_timeframe_1h` | 51.5 |
| 5 | `liqgeom.age_min_swing_any_symbol_low_fresh_below` | 51.3 |
| 6 | `liqgeom.distance_pts_swing_same_primary_any_side_wick_taken_below` | 40.4 |
| 7 | `xctx.minutes_since_last_eql_7d` | 39.2 |
| 8 | `sweep.event_type_pdl_4h` | 38.2 |
| 9 | `sweep.ed.mode_pdl_4h` | 36.2 |
| 10 | `obgeom.age_min_same_primary_any_side_fresh_above` | 34.4 |
| 11 | `liqgeom.n_members_eql_same_primary_high_fresh_above` | 34.3 |
| 12 | `liqgeom.spread_pts_eql_same_primary_any_side_wick_taken_below` | 33.3 |
| 13 | `regime.last_range_percentile_prev10_same_primary_daily_itr` | 32.8 |
| 14 | `obgeom.distance_pts_same_primary_any_side_fresh_above` | 32.2 |
| 15 | `xctx.minutes_since_last_ogap_side_gap_down_24h` | 31.7 |
| 16 | `fvggeom.age_min_same_primary_bullish_closed_through_below` | 31.3 |
| 17 | `xctx.total_events_1h` | 31.2 |
| 18 | `liqgeom.age_min_any_source_same_primary_any_side_close_taken_below` | 31.1 |
| 19 | `xctx.n_fvg_4h` | 30.4 |
| 20 | `xctx.minutes_since_last_ogap_24h` | 30.2 |
| 21 | `xctx.n_swing_side_low_7d` | 30.0 |
| 22 | `sweep.ed.ref_type_pdl` | 30.0 |
| 23 | `liqgeom.age_min_swing_same_primary_high_fresh_above` | 29.9 |
| 24 | `obgeom.age_min_any_symbol_bearish_invalidated_below` | 29.4 |
| 25 | `sweep.event_type_ny_low_1h` | 29.4 |

## Interpretation

Compare the mean test AUC to the CPU LightGBM baseline reported in `docs/ML_CONTEXT_LAYER_RESULTS.md` for the same matrix/label/side/snapshot. The two runners share encoding (`pd.get_dummies(dummy_na=True)`), split rules (`train ≤ test_year-2 / val = test_year-1 / test = test_year`), and hyperparameter shape, so the delta isolates device + library.