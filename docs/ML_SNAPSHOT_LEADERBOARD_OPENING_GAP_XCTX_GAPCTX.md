# Opening Gap Snapshot Leaderboard

_Generated `2026-05-13`._

## Setup

- Matrix: `data/ml/anchors/opening_gap_snapshots_xctx_gapctx.parquet`
- Schema: `data/ml/anchors/opening_gap_snapshots_xctx_gapctx.schema.json`
- Rows: 9,438
- Feature columns: 937
- Label columns: 122
- Grid: `at_fire` x `gap_up,gap_down,all` x 20 labels
- Split: train <= 2022, validation = 2023, test >= 2024

## Top Fixed-Split Models

| side | label | test_n | base_rate | test_auc | top_10_rate | top_lift |
|---|---|---:|---:|---:|---:|---:|
| all | `label.next_60m.resistance_rejection_3bar` | 1,854 | 27.0% | 0.933 | 87.6% | 60.6% |
| all | `label.next_240m.resistance_rejection_3bar` | 1,854 | 27.0% | 0.933 | 87.6% | 60.6% |
| all | `label.next_60m.support_rejection_3bar` | 1,854 | 36.7% | 0.923 | 95.2% | 58.5% |
| all | `label.next_240m.support_rejection_3bar` | 1,854 | 36.7% | 0.923 | 95.2% | 58.5% |
| all | `label.next_60m.resistance_break_acceptance_3bar` | 1,854 | 9.3% | 0.886 | 39.2% | 30.0% |
| all | `label.next_240m.resistance_break_acceptance_3bar` | 1,854 | 9.3% | 0.886 | 39.2% | 30.0% |
| all | `label.next_60m.support_break_acceptance_3bar` | 1,854 | 10.0% | 0.853 | 34.4% | 24.4% |
| gap_up | `label.next_60m.fully_filled` | 1,032 | 62.9% | 0.851 | 97.1% | 34.2% |

## What Works

- Support/resistance rejection labels work best.
- Break-acceptance labels also work, but base rates are lower and the top buckets are less clean.
- Gap-up fill prediction works better than gap-down fill in the top fixed split.
- The model strongly uses gap side, gap size, prior close/open price, and recent cross-concept context.

## What Does Not Work

- `touched_gap` is not useful because it is effectively always true.
- Long-horizon fill labels have high base rates, so AUC can look good while top-lift is small.
- Side-specific rejection labels are weaker than the all-side reaction models.

## Output Files

| file | purpose |
|---|---|
| `data/ml/anchors/opening_gap_snapshot_leaderboard_xctx_gapctx.csv` | CSV leaderboard |
| `data/ml/anchors/opening_gap_snapshot_leaderboard_xctx_gapctx.parquet` | Parquet leaderboard |
