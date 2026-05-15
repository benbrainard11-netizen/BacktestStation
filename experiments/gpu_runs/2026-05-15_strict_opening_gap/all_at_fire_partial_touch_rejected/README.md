# GPU XGBoost run — sweep context-layers

_Generated `2026-05-15T17:16:41.710003+00:00`._

## Setup

- matrix: `D:\BacktestStationData\strategy_lab_core_2026_05_14_context_layers\data\ml\anchors\opening_gap_snapshots_xctx_gapctx_obgeom_liqgeom_regime_strict.parquet`
- schema: `D:\BacktestStationData\strategy_lab_core_2026_05_14_context_layers\data\ml\anchors\opening_gap_snapshots_xctx_gapctx_obgeom_liqgeom_regime_strict.schema.json`
- label: `label.strict.next_240m.partial_touch_rejected`
- side: `all`
- snapshot: `at_fire`
- event_type: `all`
- device_resolved: `cuda`
- xgboost_version: `3.2.0`
- cuda_available: `True`
- seed: `20260510`
- git_sha: `7307feb570aa68d65c7eecdc7be40d8a1f7bf193`

## Per-fold metrics

| test_year | n_train | n_test | base_rate | auc_train | auc_val | auc_test | top_n | top_rate | top_lift | best_iter |
|---|---|---|---|---|---|---|---|---|---|---|
| 2020 | 3312 | 886 | 0.270 | 0.964 | 0.883 | 0.879 | 89 | 0.798 | +0.528 | 137 |
| 2021 | 4166 | 834 | 0.163 | 0.963 | 0.881 | 0.811 | 84 | 0.595 | +0.432 | 137 |
| 2022 | 5052 | 854 | 0.237 | 0.947 | 0.822 | 0.847 | 86 | 0.686 | +0.450 | 96 |
| 2023 | 5886 | 844 | 0.211 | 0.943 | 0.845 | 0.825 | 85 | 0.776 | +0.566 | 94 |
| 2024 | 6740 | 872 | 0.219 | 0.941 | 0.825 | 0.823 | 88 | 0.739 | +0.520 | 90 |
| 2025 | 7584 | 867 | 0.248 | 0.954 | 0.831 | 0.888 | 87 | 0.908 | +0.660 | 133 |

**Mean test AUC across folds:** `0.845`  
**Min-fold test AUC:** `0.811`

## Top mean-gain features (across folds)

| rank | feature | mean_gain |
|---|---|---|
| 1 | `xctx.minutes_since_last_swing_24h` | 289.9 |
| 2 | `xctx.minutes_since_last_fvg_side_bullish_24h` | 225.1 |
| 3 | `xctx.minutes_since_last_swing_side_high_7d` | 209.8 |
| 4 | `regime.minutes_since_last_same_primary_any_itr` | 191.1 |
| 5 | `xctx.minutes_since_last_swing_side_high_24h` | 170.0 |
| 6 | `xctx.n_fvg_same_primary_24h` | 165.8 |
| 7 | `xctx.minutes_since_last_fvg_24h` | 145.6 |
| 8 | `xctx.minutes_since_last_swing_7d` | 132.5 |
| 9 | `regime.minutes_since_last_same_primary_daily_itr` | 119.8 |
| 10 | `xctx.minutes_since_last_sweep_24h` | 118.9 |
| 11 | `regime.minutes_since_last_same_primary_ny_itr` | 85.3 |
| 12 | `xctx.minutes_since_last_disp_side_bearish_24h` | 72.9 |
| 13 | `xctx.minutes_since_last_orb_side_bearish_7d` | 71.9 |
| 14 | `xd.has_swing_in_24h` | 63.8 |
| 15 | `xctx.minutes_since_last_sweep_7d` | 61.7 |
| 16 | `ogap.ed.gap_size_pts` | 55.5 |
| 17 | `xctx.minutes_since_last_eql_24h` | 52.0 |
| 18 | `xctx.n_orb_same_primary_7d` | 49.7 |
| 19 | `xctx.n_swing_24h` | 48.5 |
| 20 | `xctx.minutes_since_last_disp_same_primary_24h` | 48.1 |
| 21 | `ogap.primary_symbol_YM.c.0` | 46.5 |
| 22 | `liqgeom.n_eql_same_primary_any_side_close_taken_within_100pts` | 45.0 |
| 23 | `regime.last_range_pts_same_primary_weekly_itr` | 40.7 |
| 24 | `regime.minutes_since_last_same_primary_weekly_itr` | 40.0 |
| 25 | `xctx.minutes_since_last_disp_side_bearish_7d` | 38.4 |

## Interpretation

Compare the mean test AUC to the CPU LightGBM baseline reported in `docs/ML_CONTEXT_LAYER_RESULTS.md` for the same matrix/label/side/snapshot. The two runners share encoding (`pd.get_dummies(dummy_na=True)`), split rules (`train ≤ test_year-2 / val = test_year-1 / test = test_year`), and hyperparameter shape, so the delta isolates device + library.