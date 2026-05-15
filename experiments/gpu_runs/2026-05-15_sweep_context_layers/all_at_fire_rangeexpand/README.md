# GPU XGBoost run — sweep context-layers

_Generated `2026-05-15T03:46:31.266849+00:00`._

## Setup

- matrix: `D:\BacktestStationData\strategy_lab_core_2026_05_14_context_layers\data\ml\anchors\sweep_snapshots_xctx_fvggeom_obgeom_liqgeom_regime.parquet`
- schema: `D:\BacktestStationData\strategy_lab_core_2026_05_14_context_layers\data\ml\anchors\sweep_snapshots_xctx_fvggeom_obgeom_liqgeom_regime.schema.json`
- label: `label.manipulation_range_reaction.range_expanded_2x_manipulation`
- side: `all`
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
| 2020 | 18946 | 4634 | 0.973 | 0.976 | 0.856 | 0.866 | 464 | 1.000 | +0.027 | 142 |
| 2021 | 23639 | 4867 | 0.969 | 0.994 | 0.880 | 0.928 | 487 | 1.000 | +0.031 | 298 |
| 2022 | 28273 | 4842 | 0.968 | 0.997 | 0.939 | 0.939 | 485 | 1.000 | +0.032 | 404 |
| 2023 | 33140 | 4812 | 0.960 | 0.995 | 0.946 | 0.935 | 482 | 1.000 | +0.040 | 409 |
| 2024 | 37982 | 4806 | 0.969 | 0.987 | 0.938 | 0.938 | 481 | 1.000 | +0.031 | 246 |
| 2025 | 42794 | 4757 | 0.955 | 0.976 | 0.939 | 0.875 | 476 | 0.992 | +0.037 | 157 |

**Mean test AUC across folds:** `0.913`  
**Min-fold test AUC:** `0.866`

## Top mean-gain features (across folds)

| rank | feature | mean_gain |
|---|---|---|
| 1 | `xctx.minutes_since_last_ogap_7d` | 291.6 |
| 2 | `xctx.minutes_since_last_ogap_24h` | 289.4 |
| 3 | `xctx.minutes_since_last_tp_24h` | 220.8 |
| 4 | `regime.minutes_since_last_same_primary_london_itr` | 219.3 |
| 5 | `regime.minutes_since_last_any_symbol_london_itr` | 184.1 |
| 6 | `xctx.minutes_since_last_tp_same_primary_24h` | 174.5 |
| 7 | `fvggeom.age_min_same_primary_bullish_untouched_above` | 99.7 |
| 8 | `xctx.minutes_since_last_fvg_same_primary_4h` | 84.0 |
| 9 | `fvggeom.age_min_same_primary_bearish_untouched_above` | 80.4 |
| 10 | `fvggeom.age_min_any_symbol_bearish_untouched_above` | 63.3 |
| 11 | `sweep.event_type_ny_high_1h` | 56.8 |
| 12 | `xctx.n_orb_same_primary_4h` | 55.4 |
| 13 | `regime.minutes_since_last_any_symbol_weekly_itr` | 53.6 |
| 14 | `xctx.minutes_since_last_fvg_side_bearish_4h` | 52.3 |
| 15 | `fvggeom.distance_pts_same_primary_bullish_untouched_above` | 48.1 |
| 16 | `xctx.minutes_since_last_fvg_same_primary_1h` | 47.9 |
| 17 | `fvggeom.width_pts_same_primary_bullish_tapped_above` | 45.9 |
| 18 | `xctx.n_orb_4h` | 45.7 |
| 19 | `xctx.n_macro_24h` | 45.2 |
| 20 | `xctx.has_eql_side_high_4h` | 42.9 |
| 21 | `xctx.minutes_since_last_orb_same_primary_24h` | 42.6 |
| 22 | `regime.minutes_since_last_any_symbol_daily_itr` | 42.5 |
| 23 | `xctx.minutes_since_last_orb_side_bullish_1h` | 42.4 |
| 24 | `fvggeom.n_same_primary_bullish_fully_filled_within_50pts` | 41.7 |
| 25 | `regime.minutes_since_last_same_primary_weekly_itr` | 41.2 |

## Interpretation

Compare the mean test AUC to the CPU LightGBM baseline reported in `docs/ML_CONTEXT_LAYER_RESULTS.md` for the same matrix/label/side/snapshot. The two runners share encoding (`pd.get_dummies(dummy_na=True)`), split rules (`train ≤ test_year-2 / val = test_year-1 / test = test_year`), and hyperparameter shape, so the delta isolates device + library.