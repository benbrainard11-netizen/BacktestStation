# Swing Pivot

> A swing pivot is a confirmed local high or low after enough right-side bars have printed.

## What it is

This detector records confirmed pivot highs and lows across 1H, 4H, and daily modes. A pivot is not knowable at the pivot candle itself; it is knowable only after the required right-side confirmation bars complete.

Swing pivots are mainly liquidity-map features. They mark levels that later price may take with a wick or close.

## Modes

| Mode | Meaning |
|---|---|
| `pivot_3_1h` | 1H pivot with 3-bar left/right structure |
| `pivot_5_1h` | 1H pivot with 5-bar left/right structure |
| `pivot_3_4h` | 4H pivot with 3-bar left/right structure |
| `pivot_5_4h` | 4H pivot with 5-bar left/right structure |
| `pivot_5_daily` | daily pivot with 5-bar left/right structure |

Sides are `high` and `low`.

## Where the code lives

| Component | Path |
|---|---|
| Detector | `backend/app/research/detectors/swing_pivot.py` |
| Outcomes | `backend/app/research/outcomes/swing_pivot_reactions.py` |
| Feature matrix | `data/ml/features/swing.parquet` |
| Snapshot matrix | `data/ml/anchors/swing_snapshots.parquet` |
| Snapshot leaderboard | `docs/ML_SNAPSHOT_LEADERBOARD_SWING.md` |
| Tests | `backend/tests/test_swing_pivot.py` |
| Live stats | `./stats.md` |

## What the outcomes record

The swing outcome computer records:

- `oc.breakout.wick_taken` - price wicked through the pivot level.
- `oc.breakout.close_taken` - price closed beyond the pivot level.

## ML note

For no-look-ahead ML, use `ed.knowable_ts_utc` or the generated snapshot matrix. Swing pivots are useful context, but current standalone model strength is moderate.
