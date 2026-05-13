# Opening Gap Walk-Forward

_Generated `2026-05-13`._

## Setup

- Matrix: `data/ml/anchors/opening_gap_snapshots_xctx_gapctx.parquet`
- Leaderboard source: `data/ml/anchors/opening_gap_snapshot_leaderboard_xctx_gapctx.parquet`
- Candidates: top 12 fixed-split rows
- Test years: 2020 through 2025
- Top bucket: 10% of each yearly test fold

## Top Walk-Forward Results

| side | label | folds_ok | mean_auc | min_auc | mean_base_rate | mean_top_10_rate | mean_top_lift |
|---|---|---:|---:|---:|---:|---:|---:|
| all | `label.next_60m.resistance_rejection_3bar` | 6 | 0.947 | 0.926 | 29.1% | 91.0% | 61.9% |
| all | `label.next_240m.resistance_rejection_3bar` | 6 | 0.947 | 0.926 | 29.1% | 91.0% | 61.9% |
| all | `label.next_60m.support_rejection_3bar` | 6 | 0.912 | 0.893 | 36.3% | 89.7% | 53.5% |
| all | `label.next_240m.support_rejection_3bar` | 6 | 0.912 | 0.893 | 36.3% | 89.7% | 53.5% |
| all | `label.next_60m.resistance_break_acceptance_3bar` | 6 | 0.844 | 0.802 | 9.3% | 35.1% | 25.8% |
| all | `label.next_60m.support_break_acceptance_3bar` | 6 | 0.813 | 0.724 | 9.8% | 30.4% | 20.6% |

## Interpretation

Opening gaps are now one of the cleaner research anchors in the database.

- The rejection models stayed strong year-by-year, not just in one fixed split.
- Resistance rejection is the cleanest current label.
- Support rejection is also strong.
- Break acceptance works, but it is weaker and more imbalanced.
- Fill labels are useful for context, but less valuable as headline targets because most gaps fill eventually.

## Output Files

| file | purpose |
|---|---|
| `data/ml/anchors/opening_gap_walk_forward_xctx_gapctx_summary.csv` | walk-forward summary |
| `data/ml/anchors/opening_gap_walk_forward_xctx_gapctx_summary.parquet` | walk-forward summary |
| `data/ml/anchors/opening_gap_walk_forward_xctx_gapctx_folds.csv` | per-year folds |
| `data/ml/anchors/opening_gap_walk_forward_xctx_gapctx_folds.parquet` | per-year folds |
