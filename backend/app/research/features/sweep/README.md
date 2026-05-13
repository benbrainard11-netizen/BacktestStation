# Liquidity Sweep

> A sweep records price taking a known reference high or low, then measures whether that level recovers, continues, or gets later confirmation.

## What it is

This detector watches prior day, prior week, and session highs/lows. A sweep event fires when price trades through one of those reference levels on the configured tracking timeframe.

Sweeps are useful because they describe liquidity events. The research labels ask whether the swept level recovered, whether price continued after the sweep, and whether an order block later confirmed the sweep.

## Modes

| Mode family | Examples |
|---|---|
| Prior day | `pdh_1h`, `pdh_4h`, `pdl_1h`, `pdl_4h` |
| Prior week | `pwh_4h`, `pwh_daily`, `pwl_4h`, `pwl_daily` |
| Sessions | `asia_high_1h`, `asia_low_1h`, `london_high_1h`, `london_low_1h`, `ny_high_1h`, `ny_low_1h` |

Sides are `high` and `low`.

## Where the code lives

| Component | Path |
|---|---|
| Detector | `backend/app/research/detectors/liquidity_sweep.py` |
| Outcomes | `backend/app/research/outcomes/liquidity_sweep_reactions.py` |
| Feature matrix | `data/ml/features/sweep.parquet` |
| Snapshot matrix | `data/ml/anchors/sweep_snapshots.parquet` |
| Snapshot leaderboard | `docs/ML_SNAPSHOT_LEADERBOARD_SWEEP.md` |
| Tests | `backend/tests/test_liquidity_sweep_*` |
| Live stats | `./stats.md` |

## What the outcomes record

The sweep outcome computer records:

- `oc.swept_level_recovery.level_recovered` - price recovered back through the swept level.
- `oc.forward_continuation.continued` - price continued in the sweep direction.
- `oc.ob_confirmation.did_confirm` - a later order block confirmed after the sweep.

## ML note

The easiest sweep label, OB confirmation, has a very high base rate. It is useful as a sanity check, but the more practical label is usually swept-level recovery.

Use `data/ml/anchors/sweep_snapshots.parquet` for strict no-look-ahead modeling.
