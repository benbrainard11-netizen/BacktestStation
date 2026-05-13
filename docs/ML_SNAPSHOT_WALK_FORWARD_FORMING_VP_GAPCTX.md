# Forming VP With Opening Gap Context Walk-Forward

_Generated `2026-05-13`._

## Setup

- Matrix: `data/ml/anchors/forming_vp_snapshots_xctx_gapctx.parquet`
- Leaderboard source: `data/ml/anchors/forming_vp_snapshot_leaderboard_gapctx.parquet`
- Candidates: top 12 fixed-split rows
- Test years: 2020 through 2025
- Top bucket: 10% of each yearly test fold

## Top Walk-Forward Results

| side | label | folds_ok | mean_auc | min_auc | mean_base_rate | mean_top_10_rate | mean_top_lift |
|---|---|---:|---:|---:|---:|---:|---:|
| selling | `label.next_240m.vah_touch.resistance_rejection_3bar` | 6 | 0.921 | 0.899 | 2.3% | 14.3% | 12.0% |
| selling | `label.next_240m.vah_touch.resistance_break_acceptance_3bar` | 6 | 0.919 | 0.879 | 2.3% | 13.2% | 11.0% |
| selling | `label.next_60m.took_profile_high_so_far` | 6 | 0.913 | 0.888 | 15.2% | 66.5% | 51.4% |
| all | `label.next_240m.vah_touch.resistance_rejection_3bar` | 6 | 0.892 | 0.859 | 4.5% | 22.0% | 17.5% |
| buying | `label.next_60m.vwap_touch.resistance_break_acceptance_3bar` | 6 | 0.890 | 0.841 | 4.3% | 20.9% | 16.6% |

## Comparison To Forming VP Without Gap Context

The previous forming-VP xctx best walk-forward row was:

- `selling / next_240m.vah_touch.resistance_break_acceptance_3bar`
- mean AUC 0.919
- min AUC 0.881
- mean top-decile rate 13.7%

With opening-gap memory:

- best mean AUC becomes 0.921 on the related resistance-rejection label
- the break-acceptance label is roughly flat at mean AUC 0.919
- the best mean top-decile rate is 14.3%

Interpretation: gap memory is additive context, not a major standalone upgrade for forming VP.

## Output Files

| file | purpose |
|---|---|
| `data/ml/anchors/forming_vp_walk_forward_gapctx_summary.csv` | walk-forward summary |
| `data/ml/anchors/forming_vp_walk_forward_gapctx_summary.parquet` | walk-forward summary |
| `data/ml/anchors/forming_vp_walk_forward_gapctx_folds.csv` | per-year folds |
| `data/ml/anchors/forming_vp_walk_forward_gapctx_folds.parquet` | per-year folds |
