# ML dataset roadmap

Goal: build a large, reusable, zero-look-ahead research dataset before scaling
model training on the RTX workstation.

## Principle

Every ML row is an **as-of snapshot**, not just an event. A feature is legal only
if it was knowable at that snapshot timestamp.

Core columns:

| column | meaning |
|---|---|
| `anchor.event_id` | Source research event. |
| `asof.snapshot` | Prediction point, e.g. `at_fire` or `at_period_close`. |
| `asof.snapshot_ts` | Timestamp the model is allowed to know through. |
| `asof.feature_cutoff_ts` | Hard cutoff for feature construction. |
| `asof.label_start_ts` | First timestamp of the prediction horizon. |
| `asof.label_end_ts` | End of the prediction horizon. |

## Snapshots

| snapshot | valid feature families | use case |
|---|---|---|
| `at_fire` | event-time detector features, prior cross-detector flags | Immediate reaction after detector fires. |
| `at_period_close` | `at_fire` features plus period-close status and in-window aligned events | Decide at period N close whether to position for N+1. |
| `at_next_open` | planned | Decide at N+1 open after all period-close processing is confirmed. |
| rolling intraperiod | planned | 15m/1h decision checkpoints inside period N. |

## Stage 1 shipped

Files:

| file | purpose |
|---|---|
| `backend/scripts/ml/snapshot_feature_registry.py` | Timing registry for feature prefixes and detector lags. |
| `backend/scripts/ml/build_smt_anchor_snapshot_matrix.py` | Builds SMT `at_fire` and `at_period_close` snapshot rows. |
| `backend/scripts/ml/audit_snapshot_matrix.py` | Audits snapshot timing and illegal feature presence. |
| `data/ml/anchors/smt_previous_day_snapshots.parquet` | Generated snapshot matrix. |
| `data/ml/anchors/smt_previous_day_snapshots.schema.json` | Generated schema and registry metadata. |
| `docs/ML_SNAPSHOT_AUDIT.md` | Audit report. |

Current generated shape:

| artifact | value |
|---|---|
| snapshot rows | 4,676 |
| anchors | 2,338 |
| snapshots per anchor | `at_fire`, `at_period_close` |
| feature columns | 281 |
| label columns | 18 |
| audit issues | 0 |

## Stage 2 shipped

The SMT snapshot matrix now includes richer exact aligned period-close features:

| family | examples |
|---|---|
| boolean alignment | `pc.has_1h_psp_bullish_in_window` |
| counts | `pc.n_1h_fvg_bullish_same_primary_in_window` |
| recency | `pc.minutes_since_last_4h_fvg_bullish_same_primary_in_window` |
| manual benchmark cell | `pc.manual_active_1hpsp_4hfvg_cell` |

The label set now covers N+1 and N+2 confirmation, close movement, returns,
took-period-high/low, MFE, MAE, and N+1-or-N+2 composites.

New files:

| file | purpose |
|---|---|
| `backend/scripts/ml/snapshot_model_runner.py` | Trains LightGBM from the audited snapshot matrix. |
| `backend/scripts/ml/snapshot_model_leaderboard.py` | Trains/ranks a snapshot, side, and label grid. |
| `docs/ML_SNAPSHOT_MODEL.md` | Default low-side period-close model report. |
| `docs/ML_SNAPSHOT_MODEL_AT_FIRE_LOW.md` | Low-side at-fire comparison report. |
| `docs/ML_SNAPSHOT_LEADERBOARD.md` | Snapshot model leaderboard. |
| `docs/ML_SNAPSHOT_WALK_FORWARD.md` | Rolling year-by-year validation for top leaderboard rows. |
| `data/ml/anchors/smt_snapshot_model_predictions.parquet` | Model probabilities and split tags for filtered rows. |
| `data/ml/anchors/smt_snapshot_leaderboard.parquet` | Machine-readable leaderboard results. |
| `data/ml/anchors/smt_snapshot_walk_forward_summary.parquet` | Candidate-level walk-forward summary. |
| `data/ml/anchors/smt_snapshot_walk_forward_folds.parquet` | Per-fold walk-forward results. |

Default model result:

| setup | result |
|---|---|
| anchor | `previous_day_smt`, side=`low` |
| snapshot | `at_period_close` |
| label | `label.n1_thesis_confirmed_strict` |
| test AUC | 0.865 |
| test accuracy | 0.801 |
| top 10% test bucket | 26/26 = 100.0% |
| manual cell | 28 events, 96.4% N+1, 100.0% N+1-or-N+2 |

Low-side at-fire comparison:

| setup | result |
|---|---|
| snapshot | `at_fire` |
| test AUC | 0.511 |
| top 10% test bucket | 61.5% |

Leaderboard result:

| setup | result |
|---|---|
| grid | 60/60 trained |
| labels | 10 binary labels |
| best row | `at_period_close`, side=`high`, `label.n1_thesis_confirmed_strict` |
| best test AUC | 0.910 |
| best top 10% test bucket | 28/28 = 100.0% |

Walk-forward validation result:

| setup | result |
|---|---|
| candidates | top 12 period-close leaderboard rows |
| test years | 2020, 2021, 2022, 2023, 2024, 2025 |
| folds | 72/72 trained |
| best row | `at_period_close`, side=`high`, `label.n1_thesis_confirmed_strict` |
| mean test AUC | 0.929 |
| minimum yearly AUC | 0.899 |
| mean top 10% test bucket | 98.7% |

## Stage 3 shipped

The ML research layer now has a generated catalog/manifest and SMT weekly
snapshot coverage.

New files:

| file | purpose |
|---|---|
| `backend/scripts/ml/build_ml_dataset_catalog.py` | Builds the ML dataset catalog from registries, DB coverage, feature matrices, and anchor/model artifacts. |
| `data/ml/catalog/ml_dataset_catalog.json` | Machine-readable manifest for future training jobs. |
| `docs/ML_DATASET_CATALOG.md` | Human-readable inventory of what exists and what is missing. |
| `data/ml/anchors/smt_weekly_snapshots.parquet` | Weekly SMT `at_fire` and `at_period_close` snapshot matrix. |
| `data/ml/anchors/smt_weekly_snapshots.schema.json` | Weekly SMT snapshot schema. |
| `docs/ML_SNAPSHOT_AUDIT_SMT_WEEKLY.md` | Weekly SMT snapshot audit. |
| `docs/ML_SNAPSHOT_LEADERBOARD_SMT_WEEKLY.md` | Weekly SMT initial model leaderboard. |

Current catalog result:

| item | value |
|---|---|
| research events | 603,127 |
| registered detectors | 12 |
| registered outcome computers | 12 |
| per-detector feature matrices | 12 |
| SMT snapshot event types | `previous_day_smt`, `weekly_smt` |
| non-SMT snapshot builders missing | 11 |

Weekly SMT result:

| setup | result |
|---|---|
| snapshot rows | 1,060 |
| audit issues | 0 |
| leaderboard trained | 40/60 |
| best row | `at_period_close`, side=`all`, `label.n1_thesis_confirmed_strict` |
| best test AUC | 0.861 |
| best top 10% test bucket | 81.8% |

## Stage 4 shipped

A generic conservative at-fire snapshot factory now exists for non-SMT concept
anchors.

New files:

| file | purpose |
|---|---|
| `backend/scripts/ml/build_generic_anchor_snapshots.py` | Generic at-fire snapshot builder for configured concept anchors. |
| `data/ml/anchors/fvg_snapshots.parquet` | FVG at-fire snapshot matrix. |
| `data/ml/anchors/sweep_snapshots.parquet` | Liquidity sweep at-fire snapshot matrix. |
| `data/ml/anchors/disp_snapshots.parquet` | Displacement candle at-fire snapshot matrix. |
| `docs/ML_SNAPSHOT_AUDIT_FVG.md` | FVG snapshot audit. |
| `docs/ML_SNAPSHOT_AUDIT_SWEEP.md` | Sweep snapshot audit. |
| `docs/ML_SNAPSHOT_AUDIT_DISP.md` | Displacement snapshot audit. |
| `docs/ML_SNAPSHOT_LEADERBOARD_FVG.md` | FVG at-fire leaderboard. |
| `docs/ML_SNAPSHOT_LEADERBOARD_SWEEP.md` | Sweep at-fire leaderboard. |
| `docs/ML_SNAPSHOT_LEADERBOARD_DISP.md` | Displacement at-fire leaderboard. |
| `docs/ML_CONCEPT_LEADERBOARD_SUMMARY.md` | Plain-English cross-concept summary. |

Generic snapshot result:

| anchor | rows | columns | features | labels | audit |
|---|---:|---:|---:|---:|---|
| `fvg_formation` | 209,339 | 124 | 45 | 67 | 0 issues |
| `liquidity_sweep` | 52,946 | 85 | 42 | 31 | 0 issues |
| `displacement_candle` | 38,747 | 89 | 44 | 33 | 0 issues |

Generic concept leaderboard result:

| concept | best label | best AUC | best top 10% test bucket |
|---|---|---:|---:|
| `liquidity_sweep` | `label.ob_confirmation.did_confirm` | 0.888 | 100.0% |
| `fvg_formation` | `label.mitigation.fully_filled` | 0.773 | 93.8% |
| `displacement_candle` | `label.retracement.tapped_open` | 0.681 | 90.9% |

## Next build stages

1. Expand anchor coverage:
   - PSP/OB/swing/equal-level/time-profile/volume-profile anchors.
   - Multi-anchor composite rows.

2. Add richer exact aligned features:
   - concept-specific `at_period_close` snapshots for FVG/sweep/displacement/OB.
   - first/last aligned event type in window.
   - same-primary vs cross-index split.
   - timeframe-specific family rollups.

3. Add more labels:
   - target-before-invalidation.
   - tradeable-after-costs binary.

4. Harden audits:
   - feature timestamp <= snapshot timestamp.
   - feature cutoff < label start.
   - no raw `oc.*`, `ed.*`, `ctx.*` columns in snapshot matrices.
   - snapshot-specific feature prefix validation.
   - duplicate anchor/snapshot checks.

5. Model next:
   - run the snapshot model runner across side/snapshot/label grids.
   - add walk-forward folds beyond the fixed 2022/2023/2024 split.
   - calibrate probabilities before trade sizing.
   - GPU models only after dataset semantics are stable.

## Current interpretation

The SMT edge is strongest when framed as a period-close decision. The immediate
SMT-fire model lacks valid features for the manual high-probability cell; the
period-close model can use `pc.active_at_close` and exact in-window confirmations
without look-ahead into N+1.
