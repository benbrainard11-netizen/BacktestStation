# GPU XGBoost run — sweep context-layers

_Generated `2026-05-15T03:38:49.574395+00:00`._

## Setup

- matrix: `D:\BacktestStationData\strategy_lab_core_2026_05_14_context_layers\data\ml\anchors\sweep_snapshots_xctx_fvggeom_obgeom_liqgeom_regime.parquet`
- schema: `D:\BacktestStationData\strategy_lab_core_2026_05_14_context_layers\data\ml\anchors\sweep_snapshots_xctx_fvggeom_obgeom_liqgeom_regime.schema.json`
- label: `label.ob_confirmation.did_confirm`
- side: `all`
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
| 2020 | 18946 | 4634 | 0.975 | 0.944 | 0.889 | 0.854 | 464 | 1.000 | +0.025 | 78 |
| 2021 | 23639 | 4867 | 0.973 | 0.965 | 0.866 | 0.900 | 487 | 1.000 | +0.027 | 141 |
| 2022 | 28273 | 4842 | 0.975 | 0.961 | 0.904 | 0.894 | 485 | 1.000 | +0.025 | 133 |
| 2023 | 33140 | 4812 | 0.971 | 0.944 | 0.900 | 0.923 | 482 | 1.000 | +0.029 | 79 |
| 2024 | 37982 | 4806 | 0.971 | 0.961 | 0.923 | 0.895 | 481 | 1.000 | +0.029 | 137 |
| 2025 | 42794 | 4757 | 0.971 | 0.961 | 0.899 | 0.905 | 476 | 1.000 | +0.029 | 138 |

**Mean test AUC across folds:** `0.895`  
**Min-fold test AUC:** `0.854`

## Top mean-gain features (across folds)

| rank | feature | mean_gain |
|---|---|---|
| 1 | `xctx.n_ogap_1h` | 394.7 |
| 2 | `xctx.minutes_since_last_orb_same_primary_7d` | 341.8 |
| 3 | `sweep.day_of_week` | 299.2 |
| 4 | `xctx.minutes_since_last_orb_7d` | 240.3 |
| 5 | `regime.minutes_since_last_same_primary_weekly_itr` | 170.1 |
| 6 | `sweep.ctx.day_of_week_et` | 106.8 |
| 7 | `xctx.minutes_since_last_ogap_same_primary_7d` | 94.7 |
| 8 | `sweep.ed.swept_reference.prior_period_label_session_ny` | 84.7 |
| 9 | `xctx.minutes_since_last_ft_24h` | 79.1 |
| 10 | `sweep.ed.tracking_timeframe_1h` | 77.5 |
| 11 | `xctx.minutes_since_last_ogap_7d` | 67.6 |
| 12 | `sweep.ed.swept_reference.prior_period_label_session_asia` | 65.9 |
| 13 | `regime.n_expansion_7d_same_primary_daily_itr` | 61.1 |
| 14 | `sweep.event_type_ny_high_1h` | 60.0 |
| 15 | `liqgeom.age_min_swing_same_primary_any_side_wick_taken_below` | 46.3 |
| 16 | `sweep.ctx.tracking_timeframe_1h` | 44.8 |
| 17 | `regime.n_expansion_7d_same_primary_asia_itr` | 44.7 |
| 18 | `xctx.minutes_since_last_itr_24h` | 44.1 |
| 19 | `sweep.ctx.scope_period_label_session_ny` | 40.2 |
| 20 | `xctx.minutes_since_last_itr_same_primary_4h` | 40.1 |
| 21 | `sweep.ctx.scope_period_label_globex_day` | 39.1 |
| 22 | `liqgeom.age_min_any_source_same_primary_any_side_wick_taken_below` | 38.5 |
| 23 | `regime.minutes_since_last_any_symbol_weekly_itr` | 37.9 |
| 24 | `xctx.minutes_since_last_ft_same_primary_24h` | 37.8 |
| 25 | `liqgeom.n_any_source_same_primary_high_fresh_within_25pts` | 37.5 |

## Interpretation

Compare the mean test AUC to the CPU LightGBM baseline reported in `docs/ML_CONTEXT_LAYER_RESULTS.md` for the same matrix/label/side/snapshot. The two runners share encoding (`pd.get_dummies(dummy_na=True)`), split rules (`train ≤ test_year-2 / val = test_year-1 / test = test_year`), and hyperparameter shape, so the delta isolates device + library.