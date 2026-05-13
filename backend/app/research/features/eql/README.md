# Equal Levels

> Equal levels are clustered swing highs or lows that sit close enough to act like a shared liquidity level.

## What it is

This detector builds equal-high and equal-low levels from previously confirmed swing pivots. It groups levels by pivot mode and point tolerance.

Equal levels are useful for mapping liquidity pools. The current data is better at predicting whether a level gets taken than whether the first take becomes a reversal.

## Modes

| Mode | Meaning |
|---|---|
| `eq_pivot_3_1h_5pts` | equal levels from 1H pivot-3 with 5 point tolerance |
| `eq_pivot_3_1h_15pts` | equal levels from 1H pivot-3 with 15 point tolerance |
| `eq_pivot_5_1h_5pts` | equal levels from 1H pivot-5 with 5 point tolerance |
| `eq_pivot_5_1h_15pts` | equal levels from 1H pivot-5 with 15 point tolerance |
| `eq_pivot_3_4h_15pts` | equal levels from 4H pivot-3 with 15 point tolerance |
| `eq_pivot_5_4h_15pts` | equal levels from 4H pivot-5 with 15 point tolerance |
| `eq_pivot_5_daily_30pts` | equal levels from daily pivot-5 with 30 point tolerance |

Sides are `high` and `low`.

## Where the code lives

| Component | Path |
|---|---|
| Detector | `backend/app/research/detectors/equal_levels.py` |
| Outcomes | `backend/app/research/outcomes/equal_levels_reactions.py` |
| Feature matrix | `data/ml/features/eql.parquet` |
| Snapshot matrix | `data/ml/anchors/eql_snapshots.parquet` |
| Snapshot leaderboard | `docs/ML_SNAPSHOT_LEADERBOARD_EQL.md` |
| Tests | `backend/tests/test_equal_levels.py` |
| Live stats | `./stats.md` |

## What the outcomes record

The equal-level outcome computer records:

- `oc.take.wick_taken` - price wicked through the equal level.
- `oc.take.close_past` - price closed beyond the equal level.
- `oc.take.first_take_was_reversal` - the first take behaved like a reversal.

## ML note

Equal levels should mostly feed liquidity-map context into larger models. The reversal label is weak right now; take labels are more useful.
