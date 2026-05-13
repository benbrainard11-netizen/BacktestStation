# Forming VP With Opening Gap Context Leaderboard

_Generated `2026-05-13`._

## Setup

- Matrix: `data/ml/anchors/forming_vp_snapshots_xctx_gapctx.parquet`
- Schema: `data/ml/anchors/forming_vp_snapshots_xctx_gapctx.schema.json`
- Rows: 43,150
- Feature columns: 908
- Label columns: 411
- Added context: 198 state-aware `gapctx.*` NDOG/NWOG memory features
- Split: train <= 2022, validation = 2023, test >= 2024

## Top Fixed-Split Models

| side | label | test_n | base_rate | test_auc | top_10_rate | top_lift |
|---|---|---:|---:|---:|---:|---:|
| selling | `label.next_240m.vah_touch.resistance_rejection_3bar` | 1,418 | 2.5% | 0.936 | 19.0% | 16.5% |
| selling | `label.next_240m.vah_touch.resistance_break_acceptance_3bar` | 1,418 | 2.3% | 0.928 | 16.2% | 13.9% |
| selling | `label.next_60m.vah_touch.resistance_rejection_3bar` | 1,418 | 2.3% | 0.927 | 14.8% | 12.5% |
| selling | `label.next_60m.vah_touch.resistance_break_acceptance_3bar` | 1,418 | 1.8% | 0.913 | 11.3% | 9.4% |
| selling | `label.next_60m.took_profile_high_so_far` | 1,418 | 15.7% | 0.909 | 69.7% | 54.1% |
| all | `label.next_240m.vah_touch.resistance_rejection_3bar` | 8,124 | 4.6% | 0.901 | 21.9% | 17.3% |

## Interpretation

Opening-gap memory helps enrich forming-VP rows, but it does not radically change the forming-VP story.

- The best fixed-split row is still a VAH resistance reaction model.
- The model is strong by AUC, but the base rate is low.
- Top-decile rates are useful for research ranking, not direct strategy logic.
- Compared with forming-VP xctx without gap memory, the improvement is small and label-dependent.

## Output Files

| file | purpose |
|---|---|
| `data/ml/anchors/forming_vp_snapshot_leaderboard_gapctx.csv` | CSV leaderboard |
| `data/ml/anchors/forming_vp_snapshot_leaderboard_gapctx.parquet` | Parquet leaderboard |
