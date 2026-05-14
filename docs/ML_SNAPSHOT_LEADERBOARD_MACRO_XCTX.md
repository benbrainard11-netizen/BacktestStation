# ML Snapshot Leaderboard - Macro XCTX

_Generated from `data/ml/anchors/macro_snapshot_leaderboard_xctx.csv` on 2026-05-14._

## Setup

- Matrix: `data/ml/anchors/macro_event_snapshots_xctx.parquet`
- Schema: `data/ml/anchors/macro_event_snapshots_xctx.schema.json`
- Rows: `18,414`
- Feature columns: `878`
- Label columns: `180`
- Snapshot: `at_fire`
- Sides searched: `high`, `medium`, `all`
- Labels searched: `11` main scheduled-news reaction labels
- Split: train `<= 2022`, validation `2023`, test `>= 2024`
- Model: LightGBM binary classifier
- Top bucket: highest-probability `10%` of test rows

## Output Files

| file | purpose |
|---|---|
| `data/ml/anchors/macro_snapshot_leaderboard_xctx.csv` | CSV leaderboard |
| `data/ml/anchors/macro_snapshot_leaderboard_xctx.parquet` | Parquet leaderboard |

## Coverage

| item | value |
|---|---:|
| Grid attempts | 33 |
| Trained OK | 31 |
| Skipped | 2 |

## Top Models

| snapshot | side | label | test_n | base_rate | test_auc | top_10_rate | top_lift |
|---|---|---|---:|---:|---:|---:|---:|
| at_fire | high | `label.next_15m.range_expanded_2x_pre_60m` | 1,401 | 5.2% | 0.927 | 39.0% | 33.8% |
| at_fire | all | `label.next_15m.range_expanded_2x_pre_60m` | 2,373 | 3.5% | 0.914 | 27.7% | 24.2% |
| at_fire | high | `label.next_5m.range_expanded_2x_pre_15m` | 1,400 | 7.5% | 0.872 | 46.4% | 38.9% |
| at_fire | all | `label.next_5m.range_expanded_2x_pre_15m` | 2,371 | 5.4% | 0.849 | 35.7% | 30.3% |
| at_fire | medium | `label.next_15m.took_pre_60m_high` | 972 | 29.7% | 0.819 | 73.5% | 43.7% |
| at_fire | medium | `label.next_15m.took_pre_60m_low` | 972 | 26.6% | 0.818 | 65.3% | 38.7% |
| at_fire | high | `label.next_15m.swept_both_pre_60m_sides` | 1,401 | 4.6% | 0.812 | 13.5% | 8.8% |
| at_fire | medium | `label.next_60m.range_expanded_1x_pre_60m` | 978 | 57.5% | 0.805 | 93.9% | 36.4% |
| at_fire | all | `label.next_60m.range_expanded_1x_pre_60m` | 2,382 | 60.0% | 0.805 | 95.4% | 35.4% |
| at_fire | all | `label.next_15m.took_pre_60m_high` | 2,373 | 31.9% | 0.804 | 73.9% | 42.0% |
| at_fire | all | `label.next_15m.took_pre_60m_low` | 2,373 | 27.5% | 0.804 | 75.6% | 48.1% |
| at_fire | medium | `label.next_60m.took_pre_60m_low` | 978 | 50.2% | 0.789 | 90.8% | 40.6% |

## Interpretation

- Macro release anchors have real signal for post-release volatility and range interaction.
- The strongest first-pass labels are not directional entries; they are reaction labels: will the event candle expand range, take a pre-release side, or sweep both sides.
- The best one-split scores are high enough that they must be validated with walk-forward before trusting them.
- Feature inputs are pre-release/as-of features only. Actual release values and surprise are intentionally not used as model inputs in this snapshot.
