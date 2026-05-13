# ML dataset catalog

_Generated `2026-05-13T01:23:59.406625+00:00`._

## Summary

| item | value |
|---|---|
| research_events rows | 603,127 |
| registered detectors | 12 |
| registered outcome computers | 12 |
| feature matrices | 12 |
| snapshot-builder anchor coverage | displacement_candle, equal_levels, first_third_range, fvg_formation, liquidity_sweep, opening_range_breakout, order_block, psp_candle_divergence, smt_htf_reference_divergence, swing_pivot, time_profile, volume_profile |
| catalog json | C:\Users\benbr\BacktestStation\data\ml\catalog\ml_dataset_catalog.json |

## What Already Exists

- The repo already has 12 concept detectors and 12 matching outcome modules.
- `data/ml/features` already contains per-detector feature matrices for all 12 concepts.
- Snapshot/as-of coverage currently exists for displacement_candle, equal_levels, first_third_range, fvg_formation, liquidity_sweep, opening_range_breakout, order_block, psp_candle_divergence, smt_htf_reference_divergence, swing_pivot, time_profile, volume_profile.
- SMT has richer `at_fire` plus `at_period_close` matrices; generic non-SMT coverage currently starts with conservative `at_fire` snapshots.
- The model leaderboard and walk-forward reports currently run on SMT snapshot matrices.

## Feature Matrices

| short | feature_name | rows | cols | ed | oc | binary_oc | xd | db_outcomes | min | max |
|---|---|---|---|---|---|---|---|---|---|---|
| fvg | fvg_formation | 209,339 | 121 | 23 | 75 | 5 | 11 | 100.0% | 2015-01-01 | 2026-05-08 |
| swing | swing_pivot | 76,786 | 70 | 14 | 33 | 3 | 11 | 100.0% | 2015-01-02 | 2026-05-07 |
| eql | equal_levels | 60,338 | 78 | 13 | 41 | 4 | 11 | 100.0% | 2015-01-02 | 2026-05-07 |
| sweep | liquidity_sweep | 52,946 | 83 | 20 | 37 | 4 | 11 | 100.0% | 2015-01-04 | 2026-05-08 |
| ob | order_block | 46,331 | 294 | 38 | 230 | 14 | 11 | 100.0% | 2015-01-05 | 2026-05-08 |
| disp | displacement_candle | 38,747 | 88 | 20 | 45 | 6 | 11 | 100.0% | 2015-01-02 | 2026-05-07 |
| vp | volume_profile | 36,095 | 121 | 42 | 56 | 46 | 11 | 100.0% | 2014-12-28 | 2026-05-08 |
| orb | opening_range_breakout | 34,040 | 96 | 21 | 53 | 16 | 11 | 100.0% | 2015-01-02 | 2026-05-08 |
| tp | time_profile | 19,414 | 81 | 26 | 32 | 7 | 11 | 100.0% | 2014-12-28 | 2026-05-07 |
| psp | psp_candle_divergence | 15,827 | 85 | 26 | 36 | 2 | 11 | 100.0% | 2015-01-02 | 2026-05-07 |
| ft | first_third_range | 10,373 | 94 | 20 | 52 | 15 | 11 | 100.0% | 2015-01-02 | 2026-05-08 |
| smt | smt_htf_reference_divergence | 2,891 | 118 | 44 | 49 | 11 | 11 | 100.0% | 2015-01-08 | 2026-05-05 |

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
| ft_snapshot_leaderboard.csv | csv | 42 | 30 | - | {"ok": 42} |
| ft_snapshot_leaderboard.parquet | parquet | 42 | 30 | - | {"ok": 42} |
| ft_snapshots.parquet | parquet | 10,373 | 89 | at_fire | - |
| ft_snapshots.schema.json | json | 10,373 | - | at_fire | - |
| fvg_snapshot_leaderboard.csv | csv | 15 | 30 | - | {"ok": 15} |
| fvg_snapshot_leaderboard.parquet | parquet | 15 | 30 | - | {"ok": 15} |
| fvg_snapshot_leaderboard_xctx.csv | csv | 15 | 30 | - | {"ok": 15} |
| fvg_snapshot_leaderboard_xctx.parquet | parquet | 15 | 30 | - | {"ok": 15} |
| fvg_snapshot_leaderboard_xctx_fvggeom.csv | csv | 15 | 30 | - | {"ok": 15} |
| fvg_snapshot_leaderboard_xctx_fvggeom.parquet | parquet | 15 | 30 | - | {"ok": 15} |
| fvg_snapshots.parquet | parquet | 209,339 | 124 | at_fire | - |
| fvg_snapshots.schema.json | json | 209,339 | - | at_fire | - |
| fvg_snapshots_xctx.parquet | parquet | 209,339 | 716 | at_fire | - |
| fvg_snapshots_xctx.schema.json | json | 209,339 | - | at_fire | - |
| fvg_snapshots_xctx_fvggeom.parquet | parquet | 209,339 | 1,167 | at_fire | - |
| fvg_snapshots_xctx_fvggeom.schema.json | json | 209,339 | - | at_fire | - |
| fvg_walk_forward_fvggeom_folds.csv | csv | 105 | 33 | - | {"ok": 105} |
| fvg_walk_forward_fvggeom_folds.parquet | parquet | 105 | 33 | - | {"ok": 105} |
| fvg_walk_forward_fvggeom_summary.csv | csv | 15 | 18 | - | - |
| fvg_walk_forward_fvggeom_summary.parquet | parquet | 15 | 18 | - | - |
| fvg_walk_forward_fvggeom_top5_folds.csv | csv | 25 | 33 | - | {"ok": 25} |
| fvg_walk_forward_fvggeom_top5_folds.parquet | parquet | 25 | 33 | - | {"ok": 25} |
| fvg_walk_forward_fvggeom_top5_summary.csv | csv | 5 | 18 | - | - |
| fvg_walk_forward_fvggeom_top5_summary.parquet | parquet | 5 | 18 | - | - |
| fvg_walk_forward_xctx_top5_folds.csv | csv | 25 | 33 | - | {"ok": 25} |
| fvg_walk_forward_xctx_top5_folds.parquet | parquet | 25 | 33 | - | {"ok": 25} |
| fvg_walk_forward_xctx_top5_summary.csv | csv | 5 | 18 | - | - |
| fvg_walk_forward_xctx_top5_summary.parquet | parquet | 5 | 18 | - | - |
| ob_snapshot_leaderboard.csv | csv | 39 | 30 | - | {"ok": 39} |
| ob_snapshot_leaderboard.parquet | parquet | 39 | 30 | - | {"ok": 39} |
| ob_snapshot_leaderboard_xctx.csv | csv | 39 | 30 | - | {"ok": 39} |
| ob_snapshot_leaderboard_xctx.parquet | parquet | 39 | 30 | - | {"ok": 39} |
| ob_snapshots.parquet | parquet | 46,331 | 296 | at_fire | - |
| ob_snapshots.schema.json | json | 46,331 | - | at_fire | - |
| ob_snapshots_xctx.parquet | parquet | 46,331 | 888 | at_fire | - |
| ob_snapshots_xctx.schema.json | json | 46,331 | - | at_fire | - |
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
| smt_previous_day_snapshots.parquet | parquet | 4,676 | 310 | at_fire, at_period_close | - |
| smt_previous_day_snapshots.schema.json | json | 4,676 | - | at_fire, at_period_close | - |
| smt_previous_day_snapshots_xctx.parquet | parquet | 4,676 | 902 | at_fire, at_period_close | - |
| smt_previous_day_snapshots_xctx.schema.json | json | 4,676 | - | at_fire, at_period_close | - |
| smt_previous_day_snapshots_xctx_fvggeom.parquet | parquet | 4,676 | 1,353 | at_fire, at_period_close | - |
| smt_previous_day_snapshots_xctx_fvggeom.schema.json | json | 4,676 | - | at_fire, at_period_close | - |
| smt_previous_day_walk_forward_folds_xctx.csv | csv | 48 | 33 | - | {"ok": 48} |
| smt_previous_day_walk_forward_folds_xctx.parquet | parquet | 48 | 33 | - | {"ok": 48} |
| smt_previous_day_walk_forward_fvggeom_folds.csv | csv | 126 | 33 | - | {"ok": 108, "skip_small_split": 18} |
| smt_previous_day_walk_forward_fvggeom_folds.parquet | parquet | 126 | 33 | - | {"ok": 108, "skip_small_split": 18} |
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
| sweep_snapshot_leaderboard_xctx_fvggeom.csv | csv | 9 | 30 | - | {"ok": 9} |
| sweep_snapshot_leaderboard_xctx_fvggeom.parquet | parquet | 9 | 30 | - | {"ok": 9} |
| sweep_snapshots.parquet | parquet | 52,946 | 85 | at_fire | - |
| sweep_snapshots.schema.json | json | 52,946 | - | at_fire | - |
| sweep_snapshots_xctx.parquet | parquet | 52,946 | 677 | at_fire | - |
| sweep_snapshots_xctx.schema.json | json | 52,946 | - | at_fire | - |
| sweep_snapshots_xctx_fvggeom.parquet | parquet | 52,946 | 1,128 | at_fire | - |
| sweep_snapshots_xctx_fvggeom.schema.json | json | 52,946 | - | at_fire | - |
| sweep_walk_forward_folds_base.csv | csv | 36 | 33 | - | {"ok": 36} |
| sweep_walk_forward_folds_base.parquet | parquet | 36 | 33 | - | {"ok": 36} |
| sweep_walk_forward_folds_xctx.csv | csv | 36 | 33 | - | {"ok": 36} |
| sweep_walk_forward_folds_xctx.parquet | parquet | 36 | 33 | - | {"ok": 36} |
| sweep_walk_forward_fvggeom_folds.csv | csv | 63 | 33 | - | {"ok": 63} |
| sweep_walk_forward_fvggeom_folds.parquet | parquet | 63 | 33 | - | {"ok": 63} |
| sweep_walk_forward_fvggeom_summary.csv | csv | 9 | 18 | - | - |
| sweep_walk_forward_fvggeom_summary.parquet | parquet | 9 | 18 | - | - |
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
| vp_snapshot_leaderboard_xctx.csv | csv | 180 | 30 | - | {"ok": 166, "skip_train_imbalance": 12, "skip_test_imbalance": 2} |
| vp_snapshot_leaderboard_xctx.parquet | parquet | 180 | 30 | - | {"ok": 166, "skip_train_imbalance": 12, "skip_test_imbalance": 2} |
| vp_snapshots.parquet | parquet | 36,095 | 128 | at_fire | - |
| vp_snapshots.schema.json | json | 36,095 | - | at_fire | - |
| vp_snapshots_xctx.parquet | parquet | 36,095 | 708 | at_fire | - |
| vp_snapshots_xctx.schema.json | json | 36,095 | - | at_fire | - |

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
