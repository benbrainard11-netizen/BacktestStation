# ML dataset catalog

_Generated `2026-05-15T04:06:39.213239+00:00`._

## Summary

| item | value |
|---|---|
| research_events rows | 710,224 |
| registered detectors | 16 |
| registered outcome computers | 16 |
| feature matrices | 16 |
| snapshot-builder anchor coverage | displacement_candle, equal_levels, first_third_range, forming_volume_profile, fvg_formation, interval_true_range, liquidity_sweep, macro_event_anchor, opening_gap_levels, opening_range_breakout, order_block, psp_candle_divergence, smt_htf_reference_divergence, swing_pivot, time_profile, volume_profile |
| catalog json | C:\Users\benbr\BacktestStation\data\ml\catalog\ml_dataset_catalog.json |

## What Already Exists

- The repo already has registered concept detectors and matching outcome modules.
- `data/ml/features` contains per-detector feature matrices for the registered concepts.
- Snapshot/as-of coverage currently exists for displacement_candle, equal_levels, first_third_range, forming_volume_profile, fvg_formation, interval_true_range, liquidity_sweep, macro_event_anchor, opening_gap_levels, opening_range_breakout, order_block, psp_candle_divergence, smt_htf_reference_divergence, swing_pivot, time_profile, volume_profile.
- SMT has richer `at_fire` plus `at_period_close` matrices; generic non-SMT coverage currently starts with conservative `at_fire` snapshots.
- The model leaderboard and walk-forward reports now cover multiple anchor concepts, including opening gaps and live-style forming volume profile.

## Feature Matrices

| short | feature_name | rows | cols | ed | oc | binary_oc | xd | db_outcomes | min | max |
|---|---|---|---|---|---|---|---|---|---|---|
| fvg | fvg_formation | 209,339 | 169 | 23 | 119 | 30 | 15 | 100.0% | 2015-01-01 | 2026-05-08 |
| swing | swing_pivot | 76,786 | 73 | 14 | 33 | 3 | 14 | 100.0% | 2015-01-02 | 2026-05-07 |
| eql | equal_levels | 60,338 | 81 | 13 | 41 | 4 | 14 | 100.0% | 2015-01-02 | 2026-05-07 |
| sweep | liquidity_sweep | 52,946 | 155 | 20 | 105 | 36 | 15 | 100.0% | 2015-01-04 | 2026-05-08 |
| ob | order_block | 46,331 | 297 | 38 | 230 | 14 | 14 | 100.0% | 2015-01-05 | 2026-05-08 |
| fvp | forming_volume_profile | 43,150 | 592 | 47 | 518 | 442 | 15 | 100.0% | 2015-01-02 | 2026-05-08 |
| disp | displacement_candle | 38,747 | 91 | 20 | 45 | 6 | 14 | 100.0% | 2015-01-02 | 2026-05-07 |
| itr | interval_true_range | 36,095 | 172 | 78 | 66 | 35 | 15 | 100.0% | 2015-01-02 | 2026-05-08 |
| vp | volume_profile | 36,095 | 212 | 42 | 144 | 126 | 14 | 100.0% | 2014-12-28 | 2026-05-08 |
| orb | opening_range_breakout | 34,040 | 99 | 21 | 53 | 16 | 14 | 100.0% | 2015-01-02 | 2026-05-08 |
| tp | time_profile | 19,414 | 84 | 26 | 32 | 7 | 14 | 100.0% | 2014-12-28 | 2026-05-07 |
| macro | macro_event_anchor | 18,414 | 468 | 50 | 389 | 260 | 15 | 100.0% | 2015-01-02 | 2026-05-12 |
| psp | psp_candle_divergence | 15,827 | 88 | 26 | 36 | 2 | 14 | 100.0% | 2015-01-02 | 2026-05-07 |
| ft | first_third_range | 10,373 | 97 | 20 | 52 | 15 | 14 | 100.0% | 2015-01-02 | 2026-05-08 |
| ogap | opening_gap_levels | 9,438 | 487 | 18 | 442 | 229 | 15 | 100.0% | 2015-01-04 | 2026-05-07 |
| smt | smt_htf_reference_divergence | 2,891 | 121 | 44 | 49 | 11 | 14 | 100.0% | 2015-01-08 | 2026-05-05 |

## Anchor / Model Artifacts

| artifact | kind | rows | cols | snapshots | status_counts |
|---|---|---|---|---|---|
| disp_snapshot_leaderboard.csv | csv | 15 | 30 | - | {"ok": 12, "skip_train_imbalance": 2, "skip_test_imbalance": 1} |
| disp_snapshot_leaderboard.parquet | parquet | 15 | 30 | - | {"ok": 12, "skip_train_imbalance": 2, "skip_test_imbalance": 1} |
| disp_snapshots.parquet | parquet | 38,747 | 89 | at_fire | - |
| disp_snapshots.schema.json | json | 38,747 | - | at_fire | - |
| eql_snapshot_leaderboard.csv | csv | 9 | 30 | - | {"ok": 9} |
| eql_snapshot_leaderboard.parquet | parquet | 9 | 30 | - | {"ok": 9} |
| eql_snapshots.parquet | parquet | 60,338 | 89 | at_fire | - |
| eql_snapshots.schema.json | json | 60,338 | - | at_fire | - |
| forming_vp_snapshot_leaderboard_gapctx.csv | csv | 56 | 30 | - | {"ok": 54, "skip_train_imbalance": 2} |
| forming_vp_snapshot_leaderboard_gapctx.parquet | parquet | 56 | 30 | - | {"ok": 54, "skip_train_imbalance": 2} |
| forming_vp_snapshot_leaderboard_xctx.csv | csv | 56 | 30 | - | {"ok": 54, "skip_train_imbalance": 2} |
| forming_vp_snapshot_leaderboard_xctx.parquet | parquet | 56 | 30 | - | {"ok": 54, "skip_train_imbalance": 2} |
| forming_vp_snapshots.parquet | parquet | 43,150 | 592 | at_fire | - |
| forming_vp_snapshots.schema.json | json | 43,150 | - | at_fire | - |
| forming_vp_snapshots_xctx.parquet | parquet | 43,150 | 1,388 | at_fire | - |
| forming_vp_snapshots_xctx.schema.json | json | 43,150 | - | at_fire | - |
| forming_vp_snapshots_xctx_gapctx.parquet | parquet | 43,150 | 1,586 | at_fire | - |
| forming_vp_snapshots_xctx_gapctx.schema.json | json | 43,150 | - | at_fire | - |
| forming_vp_snapshots_xctx_gapctx_obgeom.parquet | parquet | 43,150 | 2,247 | at_fire | - |
| forming_vp_snapshots_xctx_gapctx_obgeom.schema.json | json | 43,150 | - | at_fire | - |
| forming_vp_walk_forward_gapctx_folds.csv | csv | 72 | 33 | - | {"ok": 72} |
| forming_vp_walk_forward_gapctx_folds.parquet | parquet | 72 | 33 | - | {"ok": 72} |
| forming_vp_walk_forward_gapctx_summary.csv | csv | 12 | 18 | - | - |
| forming_vp_walk_forward_gapctx_summary.parquet | parquet | 12 | 18 | - | - |
| forming_vp_walk_forward_xctx_folds.csv | csv | 72 | 33 | - | {"ok": 72} |
| forming_vp_walk_forward_xctx_folds.parquet | parquet | 72 | 33 | - | {"ok": 72} |
| forming_vp_walk_forward_xctx_summary.csv | csv | 12 | 18 | - | - |
| forming_vp_walk_forward_xctx_summary.parquet | parquet | 12 | 18 | - | - |
| ft_snapshot_leaderboard.csv | csv | 42 | 30 | - | {"ok": 42} |
| ft_snapshot_leaderboard.parquet | parquet | 42 | 30 | - | {"ok": 42} |
| ft_snapshots.parquet | parquet | 10,373 | 89 | at_fire | - |
| ft_snapshots.schema.json | json | 10,373 | - | at_fire | - |
| fvg_snapshot_leaderboard.csv | csv | 15 | 30 | - | {"ok": 15} |
| fvg_snapshot_leaderboard.parquet | parquet | 15 | 30 | - | {"ok": 15} |
| fvg_snapshot_leaderboard_xctx.csv | csv | 15 | 30 | - | {"ok": 15} |
| fvg_snapshot_leaderboard_xctx.parquet | parquet | 15 | 30 | - | {"ok": 15} |
| fvg_snapshot_leaderboard_xctx_fvggeom.csv | csv | 42 | 30 | - | {"ok": 41, "skip_test_imbalance": 1} |
| fvg_snapshot_leaderboard_xctx_fvggeom.parquet | parquet | 42 | 30 | - | {"ok": 41, "skip_test_imbalance": 1} |
| fvg_snapshots.parquet | parquet | 209,339 | 170 | at_fire | - |
| fvg_snapshots.schema.json | json | 209,339 | - | at_fire | - |
| fvg_snapshots_xctx.parquet | parquet | 209,339 | 978 | at_fire | - |
| fvg_snapshots_xctx.schema.json | json | 209,339 | - | at_fire | - |
| fvg_snapshots_xctx_fvggeom.parquet | parquet | 209,339 | 1,429 | at_fire | - |
| fvg_snapshots_xctx_fvggeom.schema.json | json | 209,339 | - | at_fire | - |
| fvg_snapshots_xctx_fvggeom_obgeom.parquet | parquet | 209,339 | 2,090 | at_fire | - |
| fvg_snapshots_xctx_fvggeom_obgeom.schema.json | json | 209,339 | - | at_fire | - |
| fvg_walk_forward_fvggeom_folds.csv | csv | 72 | 33 | - | {"ok": 72} |
| fvg_walk_forward_fvggeom_folds.parquet | parquet | 72 | 33 | - | {"ok": 72} |
| fvg_walk_forward_fvggeom_summary.csv | csv | 12 | 18 | - | - |
| fvg_walk_forward_fvggeom_summary.parquet | parquet | 12 | 18 | - | - |
| fvg_walk_forward_fvggeom_top5_folds.csv | csv | 25 | 33 | - | {"ok": 25} |
| fvg_walk_forward_fvggeom_top5_folds.parquet | parquet | 25 | 33 | - | {"ok": 25} |
| fvg_walk_forward_fvggeom_top5_summary.csv | csv | 5 | 18 | - | - |
| fvg_walk_forward_fvggeom_top5_summary.parquet | parquet | 5 | 18 | - | - |
| fvg_walk_forward_xctx_top5_folds.csv | csv | 25 | 33 | - | {"ok": 25} |
| fvg_walk_forward_xctx_top5_folds.parquet | parquet | 25 | 33 | - | {"ok": 25} |
| fvg_walk_forward_xctx_top5_summary.csv | csv | 5 | 18 | - | - |
| fvg_walk_forward_xctx_top5_summary.parquet | parquet | 5 | 18 | - | - |
| itr_mode_label_leaderboard.csv | csv | 65 | 7 | - | - |
| itr_mode_leaderboard_summary.csv | csv | 5 | 8 | - | - |
| itr_snapshot_leaderboard_xctx.csv | csv | 42 | 30 | - | {"ok": 42} |
| itr_snapshot_leaderboard_xctx.parquet | parquet | 42 | 30 | - | {"ok": 42} |
| itr_snapshot_walk_forward_folds_xctx.csv | csv | 72 | 33 | - | {"ok": 72} |
| itr_snapshot_walk_forward_folds_xctx.parquet | parquet | 72 | 33 | - | {"ok": 72} |
| itr_snapshot_walk_forward_summary_xctx.csv | csv | 12 | 18 | - | - |
| itr_snapshot_walk_forward_summary_xctx.parquet | parquet | 12 | 18 | - | - |
| itr_snapshots.parquet | parquet | 36,095 | 174 | at_fire | - |
| itr_snapshots.schema.json | json | 36,095 | - | at_fire | - |
| itr_snapshots_xctx.parquet | parquet | 36,095 | 970 | at_fire | - |
| itr_snapshots_xctx.schema.json | json | 36,095 | - | at_fire | - |
| macro_event_snapshots.parquet | parquet | 18,414 | 454 | at_fire | - |
| macro_event_snapshots.schema.json | json | 18,414 | - | at_fire | - |
| macro_event_snapshots_xctx.parquet | parquet | 18,414 | 1,262 | at_fire | - |
| macro_event_snapshots_xctx.schema.json | json | 18,414 | - | at_fire | - |
| macro_event_type_breakdown.csv | csv | 70 | 56 | - | - |
| macro_event_type_breakdown.parquet | parquet | 70 | 56 | - | - |
| macro_event_type_model_leaderboard.csv | csv | 432 | 34 | - | {"ok": 194, "skip_small_split": 192, "skip_train_imbalance": 26, "skip_test_imbalance": 20} |
| macro_event_type_model_leaderboard.parquet | parquet | 432 | 34 | - | {"ok": 194, "skip_small_split": 192, "skip_train_imbalance": 26, "skip_test_imbalance": 20} |
| macro_event_type_walk_forward_folds.csv | csv | 72 | 35 | - | {"skip_small_split": 30, "ok": 23, "skip_test_imbalance": 13, "skip_train_imbalance": 6} |
| macro_event_type_walk_forward_folds.parquet | parquet | 72 | 35 | - | {"skip_small_split": 30, "ok": 23, "skip_test_imbalance": 13, "skip_train_imbalance": 6} |
| macro_event_type_walk_forward_summary.csv | csv | 12 | 19 | - | - |
| macro_event_type_walk_forward_summary.parquet | parquet | 12 | 19 | - | - |
| macro_snapshot_leaderboard_xctx.csv | csv | 48 | 30 | - | {"ok": 46, "skip_test_imbalance": 2} |
| macro_snapshot_leaderboard_xctx.parquet | parquet | 48 | 30 | - | {"ok": 46, "skip_test_imbalance": 2} |
| macro_snapshot_walk_forward_folds_xctx.csv | csv | 60 | 33 | - | {"ok": 60} |
| macro_snapshot_walk_forward_folds_xctx.parquet | parquet | 60 | 33 | - | {"ok": 60} |
| macro_snapshot_walk_forward_summary_xctx.csv | csv | 10 | 18 | - | - |
| macro_snapshot_walk_forward_summary_xctx.parquet | parquet | 10 | 18 | - | - |
| ob_snapshot_leaderboard.csv | csv | 39 | 30 | - | {"ok": 39} |
| ob_snapshot_leaderboard.parquet | parquet | 39 | 30 | - | {"ok": 39} |
| ob_snapshot_leaderboard_xctx.csv | csv | 39 | 30 | - | {"ok": 39} |
| ob_snapshot_leaderboard_xctx.parquet | parquet | 39 | 30 | - | {"ok": 39} |
| ob_snapshots.parquet | parquet | 46,331 | 296 | at_fire | - |
| ob_snapshots.schema.json | json | 46,331 | - | at_fire | - |
| ob_snapshots_xctx.parquet | parquet | 46,331 | 888 | at_fire | - |
| ob_snapshots_xctx.schema.json | json | 46,331 | - | at_fire | - |
| opening_gap_age_decay.csv | csv | 21 | 33 | - | - |
| opening_gap_snapshot_leaderboard_xctx_gapctx.csv | csv | 45 | 30 | - | {"ok": 45} |
| opening_gap_snapshot_leaderboard_xctx_gapctx.parquet | parquet | 45 | 30 | - | {"ok": 45} |
| opening_gap_snapshot_leaderboard_xctx_gapctx_obgeom_liqgeom_regime.csv | csv | 684 | 30 | - | {"ok": 530, "skip_train_imbalance": 123, "skip_test_imbalance": 31} |
| opening_gap_snapshot_leaderboard_xctx_gapctx_obgeom_liqgeom_regime.parquet | parquet | 684 | 30 | - | {"ok": 530, "skip_train_imbalance": 123, "skip_test_imbalance": 31} |
| opening_gap_snapshots.parquet | parquet | 9,438 | 449 | at_fire | - |
| opening_gap_snapshots.schema.json | json | 9,438 | - | at_fire | - |
| opening_gap_snapshots_xctx.parquet | parquet | 9,438 | 1,257 | at_fire | - |
| opening_gap_snapshots_xctx.schema.json | json | 9,438 | - | at_fire | - |
| opening_gap_snapshots_xctx_gapctx.parquet | parquet | 9,438 | 1,455 | at_fire | - |
| opening_gap_snapshots_xctx_gapctx.schema.json | json | 9,438 | - | at_fire | - |
| opening_gap_snapshots_xctx_gapctx_obgeom.parquet | parquet | 9,438 | 2,116 | at_fire | - |
| opening_gap_snapshots_xctx_gapctx_obgeom.schema.json | json | 9,438 | - | at_fire | - |
| opening_gap_snapshots_xctx_gapctx_obgeom_liqgeom.parquet | parquet | 9,438 | 3,125 | at_fire | - |
| opening_gap_snapshots_xctx_gapctx_obgeom_liqgeom.schema.json | json | 9,438 | - | at_fire | - |
| opening_gap_snapshots_xctx_gapctx_obgeom_liqgeom_regime.parquet | parquet | 9,438 | 3,281 | at_fire | - |
| opening_gap_snapshots_xctx_gapctx_obgeom_liqgeom_regime.schema.json | json | 9,438 | - | at_fire | - |
| opening_gap_walk_forward_xctx_gapctx_folds.csv | csv | 72 | 33 | - | {"ok": 72} |
| opening_gap_walk_forward_xctx_gapctx_folds.parquet | parquet | 72 | 33 | - | {"ok": 72} |
| opening_gap_walk_forward_xctx_gapctx_obgeom_liqgeom_regime_folds.csv | csv | 96 | 33 | - | {"ok": 93, "skip_test_imbalance": 3} |
| opening_gap_walk_forward_xctx_gapctx_obgeom_liqgeom_regime_folds.parquet | parquet | 96 | 33 | - | {"ok": 93, "skip_test_imbalance": 3} |
| opening_gap_walk_forward_xctx_gapctx_obgeom_liqgeom_regime_summary.csv | csv | 16 | 18 | - | - |
| opening_gap_walk_forward_xctx_gapctx_obgeom_liqgeom_regime_summary.parquet | parquet | 16 | 18 | - | - |
| opening_gap_walk_forward_xctx_gapctx_summary.csv | csv | 12 | 18 | - | - |
| opening_gap_walk_forward_xctx_gapctx_summary.parquet | parquet | 12 | 18 | - | - |
| orb_snapshot_leaderboard.csv | csv | 45 | 30 | - | {"ok": 45} |
| orb_snapshot_leaderboard.parquet | parquet | 45 | 30 | - | {"ok": 45} |
| orb_snapshots.parquet | parquet | 34,040 | 90 | at_fire | - |
| orb_snapshots.schema.json | json | 34,040 | - | at_fire | - |
| psp_snapshot_leaderboard.csv | csv | 3 | 30 | - | {"ok": 3} |
| psp_snapshot_leaderboard.parquet | parquet | 3 | 30 | - | {"ok": 3} |
| psp_snapshots.parquet | parquet | 15,827 | 96 | at_fire | - |
| psp_snapshots.schema.json | json | 15,827 | - | at_fire | - |
| smt_previous_day_snapshot_leaderboard_xctx.csv | csv | 60 | 30 | - | {"ok": 60} |
| smt_previous_day_snapshot_leaderboard_xctx.parquet | parquet | 60 | 30 | - | {"ok": 60} |
| smt_previous_day_snapshot_leaderboard_xctx_fvggeom.csv | csv | 60 | 30 | - | {"ok": 60} |
| smt_previous_day_snapshot_leaderboard_xctx_fvggeom.parquet | parquet | 60 | 30 | - | {"ok": 60} |
| smt_previous_day_snapshot_leaderboard_xctx_fvggeom_obgeom_liqgeom_regime.csv | csv | 60 | 30 | - | {"ok": 60} |
| smt_previous_day_snapshot_leaderboard_xctx_fvggeom_obgeom_liqgeom_regime.parquet | parquet | 60 | 30 | - | {"ok": 60} |
| smt_previous_day_snapshots.parquet | parquet | 4,676 | 310 | at_fire, at_period_close | - |
| smt_previous_day_snapshots.schema.json | json | 4,676 | - | at_fire, at_period_close | - |
| smt_previous_day_snapshots_xctx.parquet | parquet | 4,676 | 902 | at_fire, at_period_close | - |
| smt_previous_day_snapshots_xctx.schema.json | json | 4,676 | - | at_fire, at_period_close | - |
| smt_previous_day_snapshots_xctx_fvggeom.parquet | parquet | 4,676 | 1,353 | at_fire, at_period_close | - |
| smt_previous_day_snapshots_xctx_fvggeom.schema.json | json | 4,676 | - | at_fire, at_period_close | - |
| smt_previous_day_snapshots_xctx_fvggeom_obgeom.parquet | parquet | 4,676 | 2,014 | at_fire, at_period_close | - |
| smt_previous_day_snapshots_xctx_fvggeom_obgeom.schema.json | json | 4,676 | - | at_fire, at_period_close | - |
| smt_previous_day_snapshots_xctx_fvggeom_obgeom_liqgeom.parquet | parquet | 4,676 | 3,023 | at_fire, at_period_close | - |
| smt_previous_day_snapshots_xctx_fvggeom_obgeom_liqgeom.schema.json | json | 4,676 | - | at_fire, at_period_close | - |
| smt_previous_day_snapshots_xctx_fvggeom_obgeom_liqgeom_regime.parquet | parquet | 4,676 | 3,179 | at_fire, at_period_close | - |
| smt_previous_day_snapshots_xctx_fvggeom_obgeom_liqgeom_regime.schema.json | json | 4,676 | - | at_fire, at_period_close | - |
| smt_previous_day_walk_forward_at_fire_thesis_context_layers_folds.csv | csv | 36 | 33 | - | {"ok": 36} |
| smt_previous_day_walk_forward_at_fire_thesis_context_layers_folds.parquet | parquet | 36 | 33 | - | {"ok": 36} |
| smt_previous_day_walk_forward_at_fire_thesis_context_layers_summary.csv | csv | 6 | 18 | - | - |
| smt_previous_day_walk_forward_at_fire_thesis_context_layers_summary.parquet | parquet | 6 | 18 | - | - |
| smt_previous_day_walk_forward_folds_xctx.csv | csv | 48 | 33 | - | {"ok": 48} |
| smt_previous_day_walk_forward_folds_xctx.parquet | parquet | 48 | 33 | - | {"ok": 48} |
| smt_previous_day_walk_forward_fvggeom_folds.csv | csv | 126 | 33 | - | {"ok": 108, "skip_small_split": 18} |
| smt_previous_day_walk_forward_fvggeom_folds.parquet | parquet | 126 | 33 | - | {"ok": 108, "skip_small_split": 18} |
| smt_previous_day_walk_forward_fvggeom_obgeom_liqgeom_regime_folds.csv | csv | 48 | 33 | - | {"ok": 48} |
| smt_previous_day_walk_forward_fvggeom_obgeom_liqgeom_regime_folds.parquet | parquet | 48 | 33 | - | {"ok": 48} |
| smt_previous_day_walk_forward_fvggeom_obgeom_liqgeom_regime_summary.csv | csv | 8 | 18 | - | - |
| smt_previous_day_walk_forward_fvggeom_obgeom_liqgeom_regime_summary.parquet | parquet | 8 | 18 | - | - |
| smt_previous_day_walk_forward_fvggeom_summary.csv | csv | 18 | 18 | - | - |
| smt_previous_day_walk_forward_fvggeom_summary.parquet | parquet | 18 | 18 | - | - |
| smt_previous_day_walk_forward_summary_xctx.csv | csv | 8 | 18 | - | - |
| smt_previous_day_walk_forward_summary_xctx.parquet | parquet | 8 | 18 | - | - |
| smt_snapshot_leaderboard.csv | csv | 60 | 30 | - | {"ok": 60} |
| smt_snapshot_leaderboard.parquet | parquet | 60 | 30 | - | {"ok": 60} |
| smt_snapshot_model_predictions.parquet | parquet | 1,137 | 12 | at_period_close | - |
| smt_snapshot_model_predictions_at_fire_low.parquet | parquet | 1,137 | 12 | at_fire | - |
| smt_snapshot_walk_forward_folds.csv | csv | 72 | 33 | - | {"ok": 72} |
| smt_snapshot_walk_forward_folds.parquet | parquet | 72 | 33 | - | {"ok": 72} |
| smt_snapshot_walk_forward_summary.csv | csv | 12 | 18 | - | - |
| smt_snapshot_walk_forward_summary.parquet | parquet | 12 | 18 | - | - |
| smt_weekly_snapshot_leaderboard.csv | csv | 60 | 30 | - | {"ok": 40, "skip_small_split": 20} |
| smt_weekly_snapshot_leaderboard.parquet | parquet | 60 | 30 | - | {"ok": 40, "skip_small_split": 20} |
| smt_weekly_snapshots.parquet | parquet | 1,060 | 310 | at_fire, at_period_close | - |
| smt_weekly_snapshots.schema.json | json | 1,060 | - | at_fire, at_period_close | - |
| sweep_snapshot_leaderboard.csv | csv | 9 | 30 | - | {"ok": 9} |
| sweep_snapshot_leaderboard.parquet | parquet | 9 | 30 | - | {"ok": 9} |
| sweep_snapshot_leaderboard_xctx.csv | csv | 9 | 30 | - | {"ok": 9} |
| sweep_snapshot_leaderboard_xctx.parquet | parquet | 9 | 30 | - | {"ok": 9} |
| sweep_snapshot_leaderboard_xctx_fvggeom.csv | csv | 45 | 30 | - | {"ok": 45} |
| sweep_snapshot_leaderboard_xctx_fvggeom.parquet | parquet | 45 | 30 | - | {"ok": 45} |
| sweep_snapshot_leaderboard_xctx_fvggeom_obgeom.csv | csv | 45 | 30 | - | {"ok": 45} |
| sweep_snapshot_leaderboard_xctx_fvggeom_obgeom.parquet | parquet | 45 | 30 | - | {"ok": 45} |
| sweep_snapshot_leaderboard_xctx_fvggeom_obgeom_liqgeom_regime.csv | csv | 105 | 30 | - | {"ok": 103, "skip_train_imbalance": 2} |
| sweep_snapshot_leaderboard_xctx_fvggeom_obgeom_liqgeom_regime.parquet | parquet | 105 | 30 | - | {"ok": 103, "skip_train_imbalance": 2} |
| sweep_snapshots.parquet | parquet | 52,946 | 153 | at_fire | - |
| sweep_snapshots.schema.json | json | 52,946 | - | at_fire | - |
| sweep_snapshots_xctx.parquet | parquet | 52,946 | 961 | at_fire | - |
| sweep_snapshots_xctx.schema.json | json | 52,946 | - | at_fire | - |
| sweep_snapshots_xctx_fvggeom.parquet | parquet | 52,946 | 1,412 | at_fire | - |
| sweep_snapshots_xctx_fvggeom.schema.json | json | 52,946 | - | at_fire | - |
| sweep_snapshots_xctx_fvggeom_obgeom.parquet | parquet | 52,946 | 2,073 | at_fire | - |
| sweep_snapshots_xctx_fvggeom_obgeom.schema.json | json | 52,946 | - | at_fire | - |
| sweep_snapshots_xctx_fvggeom_obgeom_liqgeom.parquet | parquet | 52,946 | 3,082 | at_fire | - |
| sweep_snapshots_xctx_fvggeom_obgeom_liqgeom.schema.json | json | 52,946 | - | at_fire | - |
| sweep_snapshots_xctx_fvggeom_obgeom_liqgeom_regime.parquet | parquet | 52,946 | 3,238 | at_fire | - |
| sweep_snapshots_xctx_fvggeom_obgeom_liqgeom_regime.schema.json | json | 52,946 | - | at_fire | - |
| sweep_walk_forward_folds_base.csv | csv | 36 | 33 | - | {"ok": 36} |
| sweep_walk_forward_folds_base.parquet | parquet | 36 | 33 | - | {"ok": 36} |
| sweep_walk_forward_folds_xctx.csv | csv | 36 | 33 | - | {"ok": 36} |
| sweep_walk_forward_folds_xctx.parquet | parquet | 36 | 33 | - | {"ok": 36} |
| sweep_walk_forward_fvggeom_folds.csv | csv | 72 | 33 | - | {"ok": 72} |
| sweep_walk_forward_fvggeom_folds.parquet | parquet | 72 | 33 | - | {"ok": 72} |
| sweep_walk_forward_fvggeom_obgeom_folds.csv | csv | 72 | 33 | - | {"ok": 72} |
| sweep_walk_forward_fvggeom_obgeom_folds.parquet | parquet | 72 | 33 | - | {"ok": 72} |
| sweep_walk_forward_fvggeom_obgeom_liqgeom_regime_folds.csv | csv | 48 | 33 | - | {"ok": 48} |
| sweep_walk_forward_fvggeom_obgeom_liqgeom_regime_folds.parquet | parquet | 48 | 33 | - | {"ok": 48} |
| sweep_walk_forward_fvggeom_obgeom_liqgeom_regime_summary.csv | csv | 8 | 18 | - | - |
| sweep_walk_forward_fvggeom_obgeom_liqgeom_regime_summary.parquet | parquet | 8 | 18 | - | - |
| sweep_walk_forward_fvggeom_obgeom_summary.csv | csv | 12 | 18 | - | - |
| sweep_walk_forward_fvggeom_obgeom_summary.parquet | parquet | 12 | 18 | - | - |
| sweep_walk_forward_fvggeom_summary.csv | csv | 12 | 18 | - | - |
| sweep_walk_forward_fvggeom_summary.parquet | parquet | 12 | 18 | - | - |
| sweep_walk_forward_summary_base.csv | csv | 6 | 18 | - | - |
| sweep_walk_forward_summary_base.parquet | parquet | 6 | 18 | - | - |
| sweep_walk_forward_summary_xctx.csv | csv | 6 | 18 | - | - |
| sweep_walk_forward_summary_xctx.parquet | parquet | 6 | 18 | - | - |
| sweep_walk_forward_xctx_top9_folds.csv | csv | 63 | 33 | - | {"ok": 63} |
| sweep_walk_forward_xctx_top9_folds.parquet | parquet | 63 | 33 | - | {"ok": 63} |
| sweep_walk_forward_xctx_top9_summary.csv | csv | 9 | 18 | - | - |
| sweep_walk_forward_xctx_top9_summary.parquet | parquet | 9 | 18 | - | - |
| swing_snapshot_leaderboard.csv | csv | 6 | 30 | - | {"ok": 6} |
| swing_snapshot_leaderboard.parquet | parquet | 6 | 30 | - | {"ok": 6} |
| swing_snapshots.parquet | parquet | 76,786 | 78 | at_fire | - |
| swing_snapshots.schema.json | json | 76,786 | - | at_fire | - |
| tp_snapshot_leaderboard.csv | csv | 18 | 30 | - | {"ok": 18} |
| tp_snapshot_leaderboard.parquet | parquet | 18 | 30 | - | {"ok": 18} |
| tp_snapshot_leaderboard_xctx.csv | csv | 18 | 30 | - | {"ok": 18} |
| tp_snapshot_leaderboard_xctx.parquet | parquet | 18 | 30 | - | {"ok": 18} |
| tp_snapshot_leaderboard_xctx_fvggeom.csv | csv | 18 | 30 | - | {"ok": 18} |
| tp_snapshot_leaderboard_xctx_fvggeom.parquet | parquet | 18 | 30 | - | {"ok": 18} |
| tp_snapshots.parquet | parquet | 19,414 | 82 | at_fire | - |
| tp_snapshots.schema.json | json | 19,414 | - | at_fire | - |
| tp_snapshots_xctx.parquet | parquet | 19,414 | 662 | at_fire | - |
| tp_snapshots_xctx.schema.json | json | 19,414 | - | at_fire | - |
| tp_snapshots_xctx_fvggeom.parquet | parquet | 19,414 | 1,113 | at_fire | - |
| tp_snapshots_xctx_fvggeom.schema.json | json | 19,414 | - | at_fire | - |
| tp_snapshots_xctx_fvggeom_obgeom.parquet | parquet | 19,414 | 1,774 | at_fire | - |
| tp_snapshots_xctx_fvggeom_obgeom.schema.json | json | 19,414 | - | at_fire | - |
| tp_walk_forward_folds_base.csv | csv | 48 | 33 | - | {"ok": 48} |
| tp_walk_forward_folds_base.parquet | parquet | 48 | 33 | - | {"ok": 48} |
| tp_walk_forward_folds_xctx.csv | csv | 48 | 33 | - | {"ok": 48} |
| tp_walk_forward_folds_xctx.parquet | parquet | 48 | 33 | - | {"ok": 48} |
| tp_walk_forward_fvggeom_folds.csv | csv | 70 | 33 | - | {"ok": 69, "skip_small_split": 1} |
| tp_walk_forward_fvggeom_folds.parquet | parquet | 70 | 33 | - | {"ok": 69, "skip_small_split": 1} |
| tp_walk_forward_fvggeom_summary.csv | csv | 10 | 18 | - | - |
| tp_walk_forward_fvggeom_summary.parquet | parquet | 10 | 18 | - | - |
| tp_walk_forward_summary_base.csv | csv | 8 | 18 | - | - |
| tp_walk_forward_summary_base.parquet | parquet | 8 | 18 | - | - |
| tp_walk_forward_summary_xctx.csv | csv | 8 | 18 | - | - |
| tp_walk_forward_summary_xctx.parquet | parquet | 8 | 18 | - | - |
| vp_snapshot_leaderboard.csv | csv | 180 | 30 | - | {"ok": 166, "skip_train_imbalance": 12, "skip_test_imbalance": 2} |
| vp_snapshot_leaderboard.parquet | parquet | 180 | 30 | - | {"ok": 166, "skip_train_imbalance": 12, "skip_test_imbalance": 2} |
| vp_snapshot_leaderboard_v2_xctx.csv | csv | 48 | 30 | - | {"ok": 47, "skip_test_imbalance": 1} |
| vp_snapshot_leaderboard_v2_xctx.parquet | parquet | 48 | 30 | - | {"ok": 47, "skip_test_imbalance": 1} |
| vp_snapshot_leaderboard_xctx.csv | csv | 180 | 30 | - | {"ok": 166, "skip_train_imbalance": 12, "skip_test_imbalance": 2} |
| vp_snapshot_leaderboard_xctx.parquet | parquet | 180 | 30 | - | {"ok": 166, "skip_train_imbalance": 12, "skip_test_imbalance": 2} |
| vp_snapshots.parquet | parquet | 36,095 | 216 | at_fire | - |
| vp_snapshots.schema.json | json | 36,095 | - | at_fire | - |
| vp_snapshots_xctx.parquet | parquet | 36,095 | 808 | at_fire | - |
| vp_snapshots_xctx.schema.json | json | 36,095 | - | at_fire | - |
| vp_snapshots_xctx_obgeom.parquet | parquet | 36,095 | 1,469 | at_fire | - |
| vp_snapshots_xctx_obgeom.schema.json | json | 36,095 | - | at_fire | - |
| vp_walk_forward_v2_xctx_folds.csv | csv | 72 | 33 | - | {"ok": 72} |
| vp_walk_forward_v2_xctx_folds.parquet | parquet | 72 | 33 | - | {"ok": 72} |
| vp_walk_forward_v2_xctx_summary.csv | csv | 12 | 18 | - | - |
| vp_walk_forward_v2_xctx_summary.parquet | parquet | 12 | 18 | - | - |

## Gaps To Fill

| gap | items |
|---|---|
| missing feature matrix | none |
| missing outcome computer | none |
| missing SMT snapshot event type | none |
| missing snapshot builder | none |

## Recommended Next Build

The highest-leverage missing piece is **generic snapshot-builder coverage** for the remaining non-SMT concepts. The raw feature matrices exist, but they are event-time rows. The RTX-ready training database should be built from audited as-of snapshots so models can safely combine concepts without look-ahead leakage.

Suggested order:

1. Add period-close snapshot builders for `liquidity_sweep`, `fvg_formation`, `displacement_candle`, and `order_block`.
2. Add neutral future-response labels shared across anchors: forward return, MFE, MAE, took prior high/low, volatility expansion, and time-to-touch.
3. Partition snapshot outputs by `anchor=<concept>/event_type=<type>/year=<year>` once the per-concept schemas stabilize.
4. Re-run this catalog after every matrix generation so the RTX training box can discover datasets from one manifest instead of hard-coded paths.
