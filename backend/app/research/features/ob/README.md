# Order Block

> An order block is a reference candle/zone selected after a sweep, then tracked for later taps, closes, and invalidation.

## What it is

This detector builds order-block zones after prior high/low or session high/low sweeps. It records zone geometry, reference level details, and confirmation context.

Order blocks are strong in the current data, but some labels are easy because price often taps nearby OB levels. Harder labels such as deeper range tags and invalidation are more useful for research.

## Modes

| Mode family | Examples |
|---|---|
| Prior day | `swept_pdh_1h`, `swept_pdh_4h`, `swept_pdl_1h`, `swept_pdl_4h` |
| Prior week | `swept_pwh_4h`, `swept_pwh_daily`, `swept_pwl_4h`, `swept_pwl_daily` |
| Sessions | `swept_asia_high_1h`, `swept_london_low_1h`, `swept_ny_high_1h`, etc. |

Sides are `bullish` and `bearish`.

## Where the code lives

| Component | Path |
|---|---|
| Detector | `backend/app/research/detectors/order_block.py` |
| Outcomes | `backend/app/research/outcomes/order_block_reactions.py` |
| Feature matrix | `data/ml/features/ob.parquet` |
| Snapshot matrix | `data/ml/anchors/ob_snapshots.parquet` |
| Snapshot leaderboard | `docs/ML_SNAPSHOT_LEADERBOARD_OB.md` |
| Tests | `backend/tests/test_order_block_*` |
| Live stats | `./stats.md` |

## What the outcomes record

The OB outcome computer records level tags through the zone:

- `oc.level_tags.open.*`
- `oc.level_tags.q25.*`
- `oc.level_tags.q50.*`
- `oc.level_tags.q75.*`
- `oc.level_tags.close.*`
- `oc.level_tags.range_far.*`
- `oc.invalidation.invalidated`

Each tag can track wick touches and close-past behavior.

## ML note

OB has strong ranking signal, but many near-touch labels have very high base rates. For future ML, prioritize harder labels: range-far taps, close-past behavior, and invalidation.
