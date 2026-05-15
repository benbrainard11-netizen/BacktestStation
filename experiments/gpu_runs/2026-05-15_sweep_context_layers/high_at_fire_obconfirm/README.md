# GPU XGBoost run — sweep context-layers

_Generated `2026-05-15T03:47:01.729735+00:00`._

## Setup

- matrix: `D:\BacktestStationData\strategy_lab_core_2026_05_14_context_layers\data\ml\anchors\sweep_snapshots_xctx_fvggeom_obgeom_liqgeom_regime.parquet`
- schema: `D:\BacktestStationData\strategy_lab_core_2026_05_14_context_layers\data\ml\anchors\sweep_snapshots_xctx_fvggeom_obgeom_liqgeom_regime.schema.json`
- label: `label.ob_confirmation.did_confirm`
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
| 2020 | 10378 | 2624 | 0.982 | 0.944 | 0.858 | 0.897 | 263 | 1.000 | +0.018 | 92 |
| 2021 | 13094 | 2755 | 0.970 | 0.955 | 0.892 | 0.891 | 276 | 1.000 | +0.030 | 114 |
| 2022 | 15718 | 2337 | 0.976 | 0.969 | 0.892 | 0.930 | 234 | 1.000 | +0.024 | 159 |
| 2023 | 18473 | 2624 | 0.963 | 0.959 | 0.934 | 0.919 | 263 | 1.000 | +0.037 | 125 |
| 2024 | 20810 | 2635 | 0.972 | 0.966 | 0.920 | 0.891 | 264 | 1.000 | +0.028 | 150 |
| 2025 | 23434 | 2589 | 0.971 | 0.968 | 0.896 | 0.879 | 259 | 1.000 | +0.029 | 155 |

**Mean test AUC across folds:** `0.901`  
**Min-fold test AUC:** `0.879`

## Top mean-gain features (across folds)

| rank | feature | mean_gain |
|---|---|---|
| 1 | `regime.minutes_since_last_same_primary_weekly_itr` | 180.0 |
| 2 | `sweep.day_of_week` | 151.6 |
| 3 | `xd.has_fvp_in_24h` | 117.3 |
| 4 | `regime.minutes_since_last_any_symbol_weekly_itr` | 93.2 |
| 5 | `sweep.ctx.scope_period_label_globex_day` | 84.9 |
| 6 | `sweep.event_type_ny_high_1h` | 79.4 |
| 7 | `sweep.ed.mode_ny_high_1h` | 60.5 |
| 8 | `xctx.minutes_since_last_ogap_24h` | 59.5 |
| 9 | `sweep.ed.swept_reference.prior_period_label_globex_day` | 58.3 |
| 10 | `sweep.ctx.day_of_week_et` | 57.7 |
| 11 | `xctx.active_same_primary_concepts_24h` | 56.9 |
| 12 | `ts.day_of_week` | 48.8 |
| 13 | `sweep.ed.tracking_timeframe_1h` | 48.4 |
| 14 | `sweep.event_type_asia_high_1h` | 48.3 |
| 15 | `sweep.ed.ref_type_prev_ny_high` | 46.9 |
| 16 | `xctx.minutes_since_last_ogap_same_primary_7d` | 44.3 |
| 17 | `sweep.ed.mode_asia_high_1h` | 42.7 |
| 18 | `xctx.n_orb_side_bearish_24h` | 41.8 |
| 19 | `xctx.minutes_since_last_orb_24h` | 41.0 |
| 20 | `sweep.ctx.tracking_timeframe_1h` | 37.6 |
| 21 | `regime.minutes_since_last_any_symbol_ny_itr` | 37.5 |
| 22 | `xctx.total_same_primary_events_24h` | 37.3 |
| 23 | `liqgeom.age_min_eql_same_primary_high_fresh_above` | 35.2 |
| 24 | `sweep.hour_of_day_utc` | 34.4 |
| 25 | `fvggeom.width_pts_same_primary_any_side_closed_through_inside` | 32.9 |

## Interpretation

Compare the mean test AUC to the CPU LightGBM baseline reported in `docs/ML_CONTEXT_LAYER_RESULTS.md` for the same matrix/label/side/snapshot. The two runners share encoding (`pd.get_dummies(dummy_na=True)`), split rules (`train ≤ test_year-2 / val = test_year-1 / test = test_year`), and hyperparameter shape, so the delta isolates device + library.