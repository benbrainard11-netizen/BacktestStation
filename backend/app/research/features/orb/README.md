# Opening Range Breakout

> ORB records a session opening range, then measures whether price breaks high, breaks low, breaks both, or only breaks one side.

## What it is

This detector builds opening ranges for Asia and New York session windows. The event is knowable when the range window closes.

ORB is useful as session/range context. It is especially useful when the label asks for one-sided behavior, because those labels are not always true and can show meaningful lift.

## Modes

| Mode | Meaning |
|---|---|
| `asia_60m` | first 60 minutes of Asia session |
| `ny_5m` | first 5 minutes of New York session |
| `ny_15m` | first 15 minutes of New York session |
| `ny_30m` | first 30 minutes of New York session |

Sides are `bullish`, `bearish`, and `doji`.

## Where the code lives

| Component | Path |
|---|---|
| Detector | `backend/app/research/detectors/opening_range_breakout.py` |
| Outcomes | `backend/app/research/outcomes/orb_reactions.py` |
| Feature matrix | `data/ml/features/orb.parquet` |
| Snapshot matrix | `data/ml/anchors/orb_snapshots.parquet` |
| Snapshot leaderboard | `docs/ML_SNAPSHOT_LEADERBOARD_ORB.md` |
| Tests | `backend/tests/test_orb_detector.py` |
| Live stats | `./stats.md` |

## What the outcomes record

The ORB outcome computer records:

- high break behavior
- low break behavior
- extension behavior beyond the range
- `oc.broke_both_sides`
- `oc.broke_only_high`
- `oc.broke_only_low`

## ML note

Use the generated snapshot matrix so the range high/low is known but post-range breaks are labels only. ORB is currently a useful mid-tier context concept.
