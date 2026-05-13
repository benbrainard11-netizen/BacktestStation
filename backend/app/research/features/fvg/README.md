# FVG Formation

> A fair value gap is a three-candle imbalance zone where price left an untraded gap between candle 1 and candle 3.

## What it is

This detector records bullish and bearish FVG zones across multiple timeframes. The event fires when the gap is formed and the zone boundaries are knowable.

FVGs are useful because later price often trades back into the zone. The research labels measure whether the gap is tapped, filled to midpoint, fully filled, closed inside, or closed through.

## Modes

| Mode | Meaning |
|---|---|
| `15m_fvg` | 15-minute FVG |
| `1h_fvg` | 1-hour FVG |
| `4h_fvg` | 4-hour FVG |
| `daily_fvg` | daily FVG |

Sides are `bullish` and `bearish`.

## Where the code lives

| Component | Path |
|---|---|
| Detector | `backend/app/research/detectors/fvg_formation.py` |
| Outcomes | `backend/app/research/outcomes/fvg_reactions.py` |
| Feature matrix | `data/ml/features/fvg.parquet` |
| Snapshot matrix | `data/ml/anchors/fvg_snapshots.parquet` |
| Snapshot leaderboard | `docs/ML_SNAPSHOT_LEADERBOARD_FVG.md` |
| Tests | `backend/tests/test_fvg_reactions.py` |
| Live stats | `./stats.md` |

## What the outcomes record

The FVG outcome computer tracks later mitigation behavior:

- `oc.mitigation.tapped` - price touched the gap.
- `oc.mitigation.mid_filled` - price traded to the midpoint.
- `oc.mitigation.fully_filled` - price filled the whole gap.
- `oc.mitigation.closed_inside` - a candle closed inside the zone.
- `oc.mitigation.closed_through` - a candle closed through the zone.

## ML note

Use the snapshot matrix for ML work. The at-fire snapshot only includes fields knowable after the FVG forms. Do not train on `oc.*` columns as features; they are labels.

Current results live in `stats.md`. FVG has one of the best large-sample standalone concept datasets in this repo.
