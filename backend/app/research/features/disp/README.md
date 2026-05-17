# Displacement Candle

> A displacement candle is a large directional candle whose body and range stand out versus recent local context.

## What it is

This detector records bullish and bearish displacement candles on 15m, 30m, 1H, 4H, and daily timeframes. The event fires when the candle closes, because the body, range, and close location are not knowable until then.

Displacement is mainly a context feature. It helps describe momentum, confirmation, and later retracement behavior.

## Modes

| Mode | Meaning |
|---|---|
| `15m_disp` | 15-minute displacement candle |
| `30m_disp` | 30-minute displacement candle |
| `1h_disp` | 1-hour displacement candle |
| `4h_disp` | 4-hour displacement candle |
| `daily_disp` | daily displacement candle |

Sides are `bullish` and `bearish`.

## Where the code lives

| Component | Path |
|---|---|
| Detector | `backend/app/research/detectors/displacement_candle.py` |
| Outcomes | `backend/app/research/outcomes/displacement_reactions.py` |
| Feature matrix | `data/ml/features/disp.parquet` |
| Snapshot matrix | `data/ml/anchors/disp_snapshots.parquet` |
| Snapshot leaderboard | `docs/ML_SNAPSHOT_LEADERBOARD_DISP.md` |
| Tests | `backend/tests/test_displacement_*` |
| Live stats | `./stats.md` |

## What the outcomes record

The displacement outcome computer records:

- `oc.retracement.tapped_mid` - price retraced to the midpoint.
- `oc.retracement.tapped_open` - price retraced to the candle open.
- `oc.retracement.tapped_full` - price retraced the full displacement.
- `oc.invalidation.invalidated` - price invalidated the displacement level.

## ML note

Displacement is weaker as a standalone anchor than SMT, FVG, sweep, OB, TP, or VP. Keep it in the database because it is valuable as a confirmation/context feature inside larger composite models.
