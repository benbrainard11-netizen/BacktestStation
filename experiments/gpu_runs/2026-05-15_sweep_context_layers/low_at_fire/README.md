# GPU XGBoost run — sweep context-layers

_Generated `2026-05-15T03:31:32.607023+00:00`._

## Setup

- matrix: `D:\BacktestStationData\strategy_lab_core_2026_05_14_context_layers\data\ml\anchors\sweep_snapshots_xctx_fvggeom_obgeom_liqgeom_regime.parquet`
- schema: `D:\BacktestStationData\strategy_lab_core_2026_05_14_context_layers\data\ml\anchors\sweep_snapshots_xctx_fvggeom_obgeom_liqgeom_regime.schema.json`
- label: `label.manipulation_range_reaction.range_expanded_2x_manipulation`
- side: `low`
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
| 2020 | 8568 | 2010 | 0.960 | 0.990 | 0.898 | 0.876 | 201 | 1.000 | +0.040 | 242 |
| 2021 | 10545 | 2112 | 0.964 | 0.987 | 0.879 | 0.940 | 212 | 1.000 | +0.036 | 200 |
| 2022 | 12555 | 2505 | 0.967 | 0.992 | 0.947 | 0.930 | 251 | 1.000 | +0.033 | 264 |
| 2023 | 14667 | 2188 | 0.959 | 0.984 | 0.930 | 0.938 | 219 | 1.000 | +0.041 | 187 |
| 2024 | 17172 | 2171 | 0.963 | 0.987 | 0.940 | 0.934 | 218 | 1.000 | +0.037 | 208 |
| 2025 | 19360 | 2168 | 0.945 | 0.992 | 0.932 | 0.866 | 217 | 0.991 | +0.046 | 261 |

**Mean test AUC across folds:** `0.914`  
**Min-fold test AUC:** `0.866`

## Top mean-gain features (across folds)

| rank | feature | mean_gain |
|---|---|---|
| 1 | `xctx.minutes_since_last_ogap_7d` | 235.5 |
| 2 | `xctx.minutes_since_last_ogap_24h` | 234.8 |
| 3 | `xctx.minutes_since_last_tp_same_primary_24h` | 143.5 |
| 4 | `xctx.minutes_since_last_tp_24h` | 130.9 |
| 5 | `regime.minutes_since_last_same_primary_london_itr` | 129.1 |
| 6 | `regime.minutes_since_last_any_symbol_london_itr` | 94.0 |
| 7 | `fvggeom.age_min_any_symbol_bearish_untouched_above` | 71.3 |
| 8 | `fvggeom.age_min_same_primary_bearish_untouched_above` | 64.6 |
| 9 | `xctx.minutes_since_last_fvg_same_primary_4h` | 53.6 |
| 10 | `fvggeom.age_min_same_primary_bullish_untouched_above` | 53.1 |
| 11 | `xctx.minutes_since_last_fvg_same_primary_1h` | 49.2 |
| 12 | `fvggeom.distance_pts_same_primary_bullish_untouched_above` | 46.3 |
| 13 | `liqgeom.n_members_eql_same_primary_low_fresh_below` | 45.7 |
| 14 | `fvggeom.age_min_same_primary_bullish_tapped_above` | 45.6 |
| 15 | `xctx.minutes_since_last_tp_side_bearish_7d` | 41.0 |
| 16 | `fvggeom.width_pts_same_primary_bullish_tapped_above` | 40.5 |
| 17 | `obgeom.age_min_same_primary_any_side_fresh_below` | 38.5 |
| 18 | `xctx.n_macro_24h` | 36.2 |
| 19 | `xctx.n_disp_side_bullish_24h` | 35.4 |
| 20 | `xctx.n_macro_same_primary_24h` | 35.3 |
| 21 | `xctx.minutes_since_last_tp_side_bearish_24h` | 33.0 |
| 22 | `xctx.n_fvg_side_bullish_24h` | 31.9 |
| 23 | `liqgeom.distance_pts_any_source_any_symbol_low_fresh_above` | 31.8 |
| 24 | `xctx.minutes_since_last_tp_side_bearish_4h` | 31.5 |
| 25 | `regime.n_compression_7d_same_primary_london_itr` | 30.9 |

## Interpretation

Compare the mean test AUC to the CPU LightGBM baseline reported in `docs/ML_CONTEXT_LAYER_RESULTS.md` for the same matrix/label/side/snapshot. The two runners share encoding (`pd.get_dummies(dummy_na=True)`), split rules (`train ≤ test_year-2 / val = test_year-1 / test = test_year`), and hyperparameter shape, so the delta isolates device + library.