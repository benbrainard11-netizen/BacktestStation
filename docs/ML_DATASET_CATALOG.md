# ML dataset catalog

_Generated `2026-05-17T23:08:47.283850+00:00`._

## Summary

| item | value |
|---|---|
| research_events rows | 1,192,797 |
| registered detectors | 17 |
| registered outcome computers | 17 |
| feature matrices | 17 |
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
| fvg | fvg_formation | 1,243,757 | 124 | 23 | 75 | 5 | 14 | 100.0% | 2018-05-01 | 2026-04-24 |
| fvp | forming_volume_profile | 1,132,868 | 495 | 47 | 422 | 367 | 14 | 100.0% | 2018-04-30 | 2026-04-24 |
| swing | swing_pivot | 345,702 | 73 | 14 | 33 | 3 | 14 | 100.0% | 2018-05-01 | 2026-04-24 |
| smt_mtf | smt_prev_candle_divergence | 244,615 | 190 | 62 | 99 | 43 | 16 | 100.0% | 2015-01-01 | 2026-05-08 |
| sweep | liquidity_sweep | 237,569 | 82 | 20 | 33 | 4 | 14 | 100.0% | 2018-04-30 | 2026-04-24 |
| disp | displacement_candle | 214,599 | 93 | 20 | 45 | 6 | 16 | 100.0% | 2015-01-02 | 2026-05-07 |
| ob | order_block | 198,069 | 297 | 38 | 230 | 14 | 14 | 100.0% | 2018-04-30 | 2026-04-28 |
| itr | interval_true_range | 190,192 | 143 | 78 | 38 | 14 | 14 | 100.0% | 2018-05-01 | 2026-04-24 |
| vp | volume_profile | 183,662 | 212 | 42 | 144 | 126 | 14 | 100.0% | 2018-04-29 | 2026-04-24 |
| orb | opening_range_breakout | 158,941 | 99 | 21 | 53 | 16 | 14 | 100.0% | 2018-04-30 | 2026-04-24 |
| tp | time_profile | 105,819 | 84 | 26 | 32 | 7 | 14 | 100.0% | 2018-04-29 | 2026-04-23 |
| psp | psp_candle_divergence | 77,933 | 90 | 26 | 36 | 2 | 16 | 100.0% | 2015-01-02 | 2026-05-07 |
| eql | equal_levels | 61,185 | 83 | 13 | 41 | 3 | 15 | 100.0% | 2018-05-01 | 2026-04-24 |
| ft | first_third_range | 52,791 | 97 | 20 | 52 | 15 | 14 | 100.0% | 2018-05-01 | 2026-04-24 |
| ogap | opening_gap_levels | 36,944 | 210 | 18 | 166 | 73 | 14 | 100.0% | 2018-04-29 | 2026-04-23 |
| macro | macro_event_anchor | 18,414 | 468 | 50 | 389 | 260 | 15 | 100.0% | 2015-01-02 | 2026-05-12 |
| smt | smt_htf_reference_divergence | 10,889 | 301 | 224 | 49 | 11 | 14 | 100.0% | 2018-05-02 | 2026-04-23 |

## Anchor / Model Artifacts

| artifact | kind | rows | cols | snapshots | status_counts |
|---|---|---|---|---|---|
| disp_snapshot_leaderboard.csv | csv | 15 | 30 | - | {"ok": 12, "skip_train_imbalance": 2, "skip_test_imbalance": 1} |
| disp_snapshot_leaderboard.parquet | parquet | 15 | 30 | - | {"ok": 12, "skip_train_imbalance": 2, "skip_test_imbalance": 1} |
| disp_snapshots.parquet | parquet | 214,599 | 94 | at_fire | - |
| disp_snapshots.schema.json | json | 214,599 | - | at_fire | - |
| disp_snapshots_smtstate.parquet | parquet | 214,599 | 179 | at_fire | - |
| disp_snapshots_smtstate.schema.json | json | 214,599 | - | at_fire | - |
| eql_snapshot_leaderboard.csv | csv | 9 | 30 | - | {"ok": 9} |
| eql_snapshot_leaderboard.parquet | parquet | 9 | 30 | - | {"ok": 9} |
| eql_snapshots.parquet | parquet | 60,338 | 89 | at_fire | - |
| eql_snapshots.schema.json | json | 60,338 | - | at_fire | - |
| forming_vp_snapshot_leaderboard_gapctx.csv | csv | 56 | 30 | - | {"ok": 54, "skip_train_imbalance": 2} |
| forming_vp_snapshot_leaderboard_gapctx.parquet | parquet | 56 | 30 | - | {"ok": 54, "skip_train_imbalance": 2} |
| forming_vp_snapshot_leaderboard_xctx.csv | csv | 56 | 30 | - | {"ok": 54, "skip_train_imbalance": 2} |
| forming_vp_snapshot_leaderboard_xctx.parquet | parquet | 56 | 30 | - | {"ok": 54, "skip_train_imbalance": 2} |
| forming_vp_snapshots.parquet | parquet | 1,132,868 | 489 | at_fire | - |
| forming_vp_snapshots.schema.json | json | 1,132,868 | - | at_fire | - |
| forming_vp_snapshots_xctx.parquet | parquet | 1,132,868 | 1,189 | at_fire | - |
| forming_vp_snapshots_xctx.schema.json | json | 1,132,868 | - | at_fire | - |
| forming_vp_snapshots_xctx_gapctx.parquet | parquet | 1,132,868 | 1,387 | at_fire | - |
| forming_vp_snapshots_xctx_gapctx.schema.json | json | 1,132,868 | - | at_fire | - |
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
| ft_snapshots.parquet | parquet | 52,791 | 88 | at_fire | - |
| ft_snapshots.schema.json | json | 52,791 | - | at_fire | - |
| fvg_snapshot_leaderboard.csv | csv | 15 | 30 | - | {"ok": 15} |
| fvg_snapshot_leaderboard.parquet | parquet | 15 | 30 | - | {"ok": 15} |
| fvg_snapshot_leaderboard_strict_context.csv | csv | 4 | 30 | - | {"ok": 4} |
| fvg_snapshot_leaderboard_strict_context.parquet | parquet | 4 | 30 | - | {"ok": 4} |
| fvg_snapshot_leaderboard_xctx.csv | csv | 15 | 30 | - | {"ok": 15} |
| fvg_snapshot_leaderboard_xctx.parquet | parquet | 15 | 30 | - | {"ok": 15} |
| fvg_snapshot_leaderboard_xctx_fvggeom.csv | csv | 42 | 30 | - | {"ok": 41, "skip_test_imbalance": 1} |
| fvg_snapshot_leaderboard_xctx_fvggeom.parquet | parquet | 42 | 30 | - | {"ok": 41, "skip_test_imbalance": 1} |
| fvg_snapshots.parquet | parquet | 1,243,757 | 123 | at_fire | - |
| fvg_snapshots.schema.json | json | 1,243,757 | - | at_fire | - |
| fvg_snapshots_smtstate.parquet | parquet | 1,243,757 | 208 | at_fire | - |
| fvg_snapshots_smtstate.schema.json | json | 1,243,757 | - | at_fire | - |
| fvg_snapshots_xctx.parquet | parquet | 1,243,757 | 835 | at_fire | - |
| fvg_snapshots_xctx.schema.json | json | 1,243,757 | - | at_fire | - |
| fvg_snapshots_xctx_fvggeom.parquet | parquet | 1,243,757 | 1,286 | at_fire | - |
| fvg_snapshots_xctx_fvggeom.schema.json | json | 1,243,757 | - | at_fire | - |
| fvg_snapshots_xctx_fvggeom_obgeom.parquet | parquet | 209,339 | 2,090 | at_fire | - |
| fvg_snapshots_xctx_fvggeom_obgeom.schema.json | json | 209,339 | - | at_fire | - |
| fvg_snapshots_xctx_fvggeom_obgeom_strict.parquet | parquet | 209,339 | 2,114 | at_fire | - |
| fvg_snapshots_xctx_fvggeom_obgeom_strict.schema.json | json | 209,339 | - | at_fire | - |
| fvg_strict_label_stats.csv | csv | 360 | 6 | - | - |
| fvg_walk_forward_fvggeom_folds.csv | csv | 72 | 33 | - | {"ok": 72} |
| fvg_walk_forward_fvggeom_folds.parquet | parquet | 72 | 33 | - | {"ok": 72} |
| fvg_walk_forward_fvggeom_summary.csv | csv | 12 | 18 | - | - |
| fvg_walk_forward_fvggeom_summary.parquet | parquet | 12 | 18 | - | - |
| fvg_walk_forward_fvggeom_top5_folds.csv | csv | 25 | 33 | - | {"ok": 25} |
| fvg_walk_forward_fvggeom_top5_folds.parquet | parquet | 25 | 33 | - | {"ok": 25} |
| fvg_walk_forward_fvggeom_top5_summary.csv | csv | 5 | 18 | - | - |
| fvg_walk_forward_fvggeom_top5_summary.parquet | parquet | 5 | 18 | - | - |
| fvg_walk_forward_strict_context_folds.csv | csv | 24 | 33 | - | {"ok": 24} |
| fvg_walk_forward_strict_context_folds.parquet | parquet | 24 | 33 | - | {"ok": 24} |
| fvg_walk_forward_strict_context_summary.csv | csv | 4 | 18 | - | - |
| fvg_walk_forward_strict_context_summary.parquet | parquet | 4 | 18 | - | - |
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
| itr_snapshots.parquet | parquet | 190,192 | 142 | at_fire | - |
| itr_snapshots.schema.json | json | 190,192 | - | at_fire | - |
| itr_snapshots_xctx.parquet | parquet | 190,192 | 842 | at_fire | - |
| itr_snapshots_xctx.schema.json | json | 190,192 | - | at_fire | - |
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
| macro_news_interaction_summary.csv | csv | 260 | 8 | - | - |
| macro_news_interaction_summary.parquet | parquet | 260 | 8 | - | - |
| macro_news_interactions.parquet | parquet | 18,414 | 606 | - | - |
| macro_news_interactions.schema.json | json | 18,414 | - | - | - |
| macro_news_level_reaction_stats.csv | csv | 785 | 17 | - | - |
| macro_news_level_reaction_stats.parquet | parquet | 785 | 17 | - | - |
| macro_snapshot_leaderboard_xctx.csv | csv | 48 | 30 | - | {"ok": 46, "skip_test_imbalance": 2} |
| macro_snapshot_leaderboard_xctx.parquet | parquet | 48 | 30 | - | {"ok": 46, "skip_test_imbalance": 2} |
| macro_snapshot_walk_forward_folds_xctx.csv | csv | 60 | 33 | - | {"ok": 60} |
| macro_snapshot_walk_forward_folds_xctx.parquet | parquet | 60 | 33 | - | {"ok": 60} |
| macro_snapshot_walk_forward_summary_xctx.csv | csv | 10 | 18 | - | - |
| macro_snapshot_walk_forward_summary_xctx.parquet | parquet | 10 | 18 | - | - |
| ob_snapshot_leaderboard.csv | csv | 39 | 30 | - | {"ok": 39} |
| ob_snapshot_leaderboard.parquet | parquet | 39 | 30 | - | {"ok": 39} |
| ob_snapshot_leaderboard_strict_context.csv | csv | 30 | 30 | - | {"ok": 30} |
| ob_snapshot_leaderboard_strict_context.parquet | parquet | 30 | 30 | - | {"ok": 30} |
| ob_snapshot_leaderboard_xctx.csv | csv | 39 | 30 | - | {"ok": 39} |
| ob_snapshot_leaderboard_xctx.parquet | parquet | 39 | 30 | - | {"ok": 39} |
| ob_snapshots.parquet | parquet | 198,069 | 291 | at_fire | - |
| ob_snapshots.schema.json | json | 198,069 | - | at_fire | - |
| ob_snapshots_smtstate.parquet | parquet | 198,069 | 376 | at_fire | - |
| ob_snapshots_smtstate.schema.json | json | 198,069 | - | at_fire | - |
| ob_snapshots_xctx.parquet | parquet | 46,331 | 888 | at_fire | - |
| ob_snapshots_xctx.schema.json | json | 46,331 | - | at_fire | - |
| ob_snapshots_xctx_strict.parquet | parquet | 46,331 | 898 | at_fire | - |
| ob_snapshots_xctx_strict.schema.json | json | 46,331 | - | at_fire | - |
| ob_strict_label_stats.csv | csv | 450 | 6 | - | - |
| ob_walk_forward_strict_context_folds.csv | csv | 48 | 33 | - | {"ok": 48} |
| ob_walk_forward_strict_context_folds.parquet | parquet | 48 | 33 | - | {"ok": 48} |
| ob_walk_forward_strict_context_summary.csv | csv | 8 | 18 | - | - |
| ob_walk_forward_strict_context_summary.parquet | parquet | 8 | 18 | - | - |
| opening_gap_age_decay.csv | csv | 21 | 33 | - | - |
| opening_gap_snapshot_leaderboard_strict_context.csv | csv | 81 | 30 | - | {"ok": 75, "skip_train_imbalance": 5, "skip_test_imbalance": 1} |
| opening_gap_snapshot_leaderboard_strict_context.parquet | parquet | 81 | 30 | - | {"ok": 75, "skip_train_imbalance": 5, "skip_test_imbalance": 1} |
| opening_gap_snapshot_leaderboard_xctx_gapctx.csv | csv | 45 | 30 | - | {"ok": 45} |
| opening_gap_snapshot_leaderboard_xctx_gapctx.parquet | parquet | 45 | 30 | - | {"ok": 45} |
| opening_gap_snapshot_leaderboard_xctx_gapctx_obgeom_liqgeom_regime.csv | csv | 684 | 30 | - | {"ok": 530, "skip_train_imbalance": 123, "skip_test_imbalance": 31} |
| opening_gap_snapshot_leaderboard_xctx_gapctx_obgeom_liqgeom_regime.parquet | parquet | 684 | 30 | - | {"ok": 530, "skip_train_imbalance": 123, "skip_test_imbalance": 31} |
| opening_gap_snapshots.parquet | parquet | 36,944 | 168 | at_fire | - |
| opening_gap_snapshots.schema.json | json | 36,944 | - | at_fire | - |
| opening_gap_snapshots_xctx.parquet | parquet | 36,944 | 880 | at_fire | - |
| opening_gap_snapshots_xctx.schema.json | json | 36,944 | - | at_fire | - |
| opening_gap_snapshots_xctx_gapctx.parquet | parquet | 36,944 | 1,078 | at_fire | - |
| opening_gap_snapshots_xctx_gapctx.schema.json | json | 36,944 | - | at_fire | - |
| opening_gap_snapshots_xctx_gapctx_obgeom.parquet | parquet | 9,438 | 2,116 | at_fire | - |
| opening_gap_snapshots_xctx_gapctx_obgeom.schema.json | json | 9,438 | - | at_fire | - |
| opening_gap_snapshots_xctx_gapctx_obgeom_liqgeom.parquet | parquet | 9,438 | 3,125 | at_fire | - |
| opening_gap_snapshots_xctx_gapctx_obgeom_liqgeom.schema.json | json | 9,438 | - | at_fire | - |
| opening_gap_snapshots_xctx_gapctx_obgeom_liqgeom_regime.parquet | parquet | 9,438 | 3,281 | at_fire | - |
| opening_gap_snapshots_xctx_gapctx_obgeom_liqgeom_regime.schema.json | json | 9,438 | - | at_fire | - |
| opening_gap_snapshots_xctx_gapctx_obgeom_liqgeom_regime_strict.parquet | parquet | 9,438 | 3,308 | at_fire | - |
| opening_gap_snapshots_xctx_gapctx_obgeom_liqgeom_regime_strict.schema.json | json | 9,438 | - | at_fire | - |
| opening_gap_strict_context_leaderboard.csv | csv | 60 | 30 | - | {"ok": 57, "skip_train_imbalance": 2, "skip_test_imbalance": 1} |
| opening_gap_strict_context_leaderboard.parquet | parquet | 60 | 30 | - | {"ok": 57, "skip_train_imbalance": 2, "skip_test_imbalance": 1} |
| opening_gap_strict_context_walk_forward_folds.csv | csv | 72 | 33 | - | {"ok": 72} |
| opening_gap_strict_context_walk_forward_folds.parquet | parquet | 72 | 33 | - | {"ok": 72} |
| opening_gap_strict_context_walk_forward_summary.csv | csv | 12 | 18 | - | - |
| opening_gap_strict_context_walk_forward_summary.parquet | parquet | 12 | 18 | - | - |
| opening_gap_strict_label_stats.csv | csv | 81 | 5 | - | - |
| opening_gap_walk_forward_strict_context_folds.csv | csv | 72 | 33 | - | {"ok": 72} |
| opening_gap_walk_forward_strict_context_folds.parquet | parquet | 72 | 33 | - | {"ok": 72} |
| opening_gap_walk_forward_strict_context_summary.csv | csv | 12 | 18 | - | - |
| opening_gap_walk_forward_strict_context_summary.parquet | parquet | 12 | 18 | - | - |
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
| orb_snapshots.parquet | parquet | 158,941 | 90 | at_fire | - |
| orb_snapshots.schema.json | json | 158,941 | - | at_fire | - |
| psp_snapshot_leaderboard.csv | csv | 3 | 30 | - | {"ok": 3} |
| psp_snapshot_leaderboard.parquet | parquet | 3 | 30 | - | {"ok": 3} |
| psp_snapshots.parquet | parquet | 77,933 | 101 | at_fire | - |
| psp_snapshots.schema.json | json | 77,933 | - | at_fire | - |
| psp_snapshots_smtstate.parquet | parquet | 77,933 | 186 | at_fire | - |
| psp_snapshots_smtstate.schema.json | json | 77,933 | - | at_fire | - |
| smt_previous_day_snapshot_leaderboard_xctx.csv | csv | 60 | 30 | - | {"ok": 60} |
| smt_previous_day_snapshot_leaderboard_xctx.parquet | parquet | 60 | 30 | - | {"ok": 60} |
| smt_previous_day_snapshot_leaderboard_xctx_fvggeom.csv | csv | 60 | 30 | - | {"ok": 60} |
| smt_previous_day_snapshot_leaderboard_xctx_fvggeom.parquet | parquet | 60 | 30 | - | {"ok": 60} |
| smt_previous_day_snapshot_leaderboard_xctx_fvggeom_obgeom_liqgeom_regime.csv | csv | 60 | 30 | - | {"ok": 60} |
| smt_previous_day_snapshot_leaderboard_xctx_fvggeom_obgeom_liqgeom_regime.parquet | parquet | 60 | 30 | - | {"ok": 60} |
| smt_previous_day_snapshots.parquet | parquet | 15,690 | 343 | at_fire, at_period_close | - |
| smt_previous_day_snapshots.schema.json | json | 15,690 | - | at_fire, at_period_close | - |
| smt_previous_day_snapshots_xctx.parquet | parquet | 15,690 | 1,055 | at_fire, at_period_close | - |
| smt_previous_day_snapshots_xctx.schema.json | json | 15,690 | - | at_fire, at_period_close | - |
| smt_previous_day_snapshots_xctx_fvggeom.parquet | parquet | 15,690 | 1,506 | at_fire, at_period_close | - |
| smt_previous_day_snapshots_xctx_fvggeom.schema.json | json | 15,690 | - | at_fire, at_period_close | - |
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
| smt_weekly_snapshots.parquet | parquet | 5,964 | 343 | at_fire, at_period_close | - |
| smt_weekly_snapshots.schema.json | json | 5,964 | - | at_fire, at_period_close | - |
| smt_weekly_snapshots_xctx.parquet | parquet | 5,964 | 1,055 | at_fire, at_period_close | - |
| smt_weekly_snapshots_xctx.schema.json | json | 5,964 | - | at_fire, at_period_close | - |
| smt_weekly_snapshots_xctx_fvggeom.parquet | parquet | 5,964 | 1,506 | at_fire, at_period_close | - |
| smt_weekly_snapshots_xctx_fvggeom.schema.json | json | 5,964 | - | at_fire, at_period_close | - |
| sweep_snapshot_leaderboard.csv | csv | 9 | 30 | - | {"ok": 9} |
| sweep_snapshot_leaderboard.parquet | parquet | 9 | 30 | - | {"ok": 9} |
| sweep_snapshot_leaderboard_strict_context.csv | csv | 30 | 30 | - | {"ok": 30} |
| sweep_snapshot_leaderboard_strict_context.parquet | parquet | 30 | 30 | - | {"ok": 30} |
| sweep_snapshot_leaderboard_xctx.csv | csv | 9 | 30 | - | {"ok": 9} |
| sweep_snapshot_leaderboard_xctx.parquet | parquet | 9 | 30 | - | {"ok": 9} |
| sweep_snapshot_leaderboard_xctx_fvggeom.csv | csv | 45 | 30 | - | {"ok": 45} |
| sweep_snapshot_leaderboard_xctx_fvggeom.parquet | parquet | 45 | 30 | - | {"ok": 45} |
| sweep_snapshot_leaderboard_xctx_fvggeom_obgeom.csv | csv | 45 | 30 | - | {"ok": 45} |
| sweep_snapshot_leaderboard_xctx_fvggeom_obgeom.parquet | parquet | 45 | 30 | - | {"ok": 45} |
| sweep_snapshot_leaderboard_xctx_fvggeom_obgeom_liqgeom_regime.csv | csv | 105 | 30 | - | {"ok": 103, "skip_train_imbalance": 2} |
| sweep_snapshot_leaderboard_xctx_fvggeom_obgeom_liqgeom_regime.parquet | parquet | 105 | 30 | - | {"ok": 103, "skip_train_imbalance": 2} |
| sweep_snapshots.parquet | parquet | 237,569 | 73 | at_fire | - |
| sweep_snapshots.schema.json | json | 237,569 | - | at_fire | - |
| sweep_snapshots_smtstate.parquet | parquet | 237,569 | 158 | at_fire | - |
| sweep_snapshots_smtstate.schema.json | json | 237,569 | - | at_fire | - |
| sweep_snapshots_xctx.parquet | parquet | 237,569 | 785 | at_fire | - |
| sweep_snapshots_xctx.schema.json | json | 237,569 | - | at_fire | - |
| sweep_snapshots_xctx_fvggeom.parquet | parquet | 237,569 | 1,236 | at_fire | - |
| sweep_snapshots_xctx_fvggeom.schema.json | json | 237,569 | - | at_fire | - |
| sweep_snapshots_xctx_fvggeom_obgeom.parquet | parquet | 52,946 | 2,073 | at_fire | - |
| sweep_snapshots_xctx_fvggeom_obgeom.schema.json | json | 52,946 | - | at_fire | - |
| sweep_snapshots_xctx_fvggeom_obgeom_liqgeom.parquet | parquet | 52,946 | 3,082 | at_fire | - |
| sweep_snapshots_xctx_fvggeom_obgeom_liqgeom.schema.json | json | 52,946 | - | at_fire | - |
| sweep_snapshots_xctx_fvggeom_obgeom_liqgeom_regime.parquet | parquet | 52,946 | 3,238 | at_fire | - |
| sweep_snapshots_xctx_fvggeom_obgeom_liqgeom_regime.schema.json | json | 52,946 | - | at_fire | - |
| sweep_snapshots_xctx_fvggeom_obgeom_liqgeom_regime_strict.parquet | parquet | 52,946 | 3,248 | at_fire | - |
| sweep_snapshots_xctx_fvggeom_obgeom_liqgeom_regime_strict.schema.json | json | 52,946 | - | at_fire | - |
| sweep_strict_label_stats.csv | csv | 450 | 6 | - | - |
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
| sweep_walk_forward_strict_context_folds.csv | csv | 24 | 33 | - | {"ok": 24} |
| sweep_walk_forward_strict_context_folds.parquet | parquet | 24 | 33 | - | {"ok": 24} |
| sweep_walk_forward_strict_context_summary.csv | csv | 4 | 18 | - | - |
| sweep_walk_forward_strict_context_summary.parquet | parquet | 4 | 18 | - | - |
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
| swing_snapshot_leaderboard_strict_context.csv | csv | 30 | 30 | - | {"ok": 30} |
| swing_snapshot_leaderboard_strict_context.parquet | parquet | 30 | 30 | - | {"ok": 30} |
| swing_snapshots.parquet | parquet | 345,702 | 77 | at_fire | - |
| swing_snapshots.schema.json | json | 345,702 | - | at_fire | - |
| swing_snapshots_strict.parquet | parquet | 76,786 | 88 | at_fire | - |
| swing_snapshots_strict.schema.json | json | 76,786 | - | at_fire | - |
| swing_strict_label_stats.csv | csv | 180 | 6 | - | - |
| swing_walk_forward_strict_context_folds.csv | csv | 48 | 33 | - | {"ok": 48} |
| swing_walk_forward_strict_context_folds.parquet | parquet | 48 | 33 | - | {"ok": 48} |
| swing_walk_forward_strict_context_summary.csv | csv | 8 | 18 | - | - |
| swing_walk_forward_strict_context_summary.parquet | parquet | 8 | 18 | - | - |
| tp_snapshot_leaderboard.csv | csv | 18 | 30 | - | {"ok": 18} |
| tp_snapshot_leaderboard.parquet | parquet | 18 | 30 | - | {"ok": 18} |
| tp_snapshot_leaderboard_xctx.csv | csv | 18 | 30 | - | {"ok": 18} |
| tp_snapshot_leaderboard_xctx.parquet | parquet | 18 | 30 | - | {"ok": 18} |
| tp_snapshot_leaderboard_xctx_fvggeom.csv | csv | 18 | 30 | - | {"ok": 18} |
| tp_snapshot_leaderboard_xctx_fvggeom.parquet | parquet | 18 | 30 | - | {"ok": 18} |
| tp_snapshots.parquet | parquet | 105,819 | 77 | at_fire | - |
| tp_snapshots.schema.json | json | 105,819 | - | at_fire | - |
| tp_snapshots_xctx.parquet | parquet | 105,819 | 777 | at_fire | - |
| tp_snapshots_xctx.schema.json | json | 105,819 | - | at_fire | - |
| tp_snapshots_xctx_fvggeom.parquet | parquet | 105,819 | 1,228 | at_fire | - |
| tp_snapshots_xctx_fvggeom.schema.json | json | 105,819 | - | at_fire | - |
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
| vp_snapshots.parquet | parquet | 183,662 | 213 | at_fire | - |
| vp_snapshots.schema.json | json | 183,662 | - | at_fire | - |
| vp_snapshots_xctx.parquet | parquet | 183,662 | 913 | at_fire | - |
| vp_snapshots_xctx.schema.json | json | 183,662 | - | at_fire | - |
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
| missing snapshot builder | smt_prev_candle_divergence |

## Recommended Next Build

The highest-leverage missing piece is **generic snapshot-builder coverage** for the remaining non-SMT concepts. The raw feature matrices exist, but they are event-time rows. The RTX-ready training database should be built from audited as-of snapshots so models can safely combine concepts without look-ahead leakage.

Suggested order:

1. Add period-close snapshot builders for `liquidity_sweep`, `fvg_formation`, `displacement_candle`, and `order_block`.
2. Add neutral future-response labels shared across anchors: forward return, MFE, MAE, took prior high/low, volatility expansion, and time-to-touch.
3. Partition snapshot outputs by `anchor=<concept>/event_type=<type>/year=<year>` once the per-concept schemas stabilize.
4. Re-run this catalog after every matrix generation so the RTX training box can discover datasets from one manifest instead of hard-coded paths.
