# First-Third Range

> First-third range captures the first third of a parent period, then measures how the rest of that period behaves.

## What it is

This detector divides a daily or weekly parent period into thirds. It records the range and direction of the first third once that window closes.

The concept is useful for range-expansion context: does the rest of the period confirm the first-third direction, reverse it, break one side, or extend beyond the range?

## Modes

| Mode | Meaning |
|---|---|
| `first_third_daily` | first third of a daily parent period |
| `first_third_weekly` | first third of a weekly parent period |

Sides are `bullish`, `bearish`, and `doji`.

## Where the code lives

| Component | Path |
|---|---|
| Detector | `backend/app/research/detectors/first_third_range.py` |
| Outcomes | `backend/app/research/outcomes/first_third_reactions.py` |
| Feature matrix | `data/ml/features/ft.parquet` |
| Snapshot matrix | `data/ml/anchors/ft_snapshots.parquet` |
| Snapshot leaderboard | `docs/ML_SNAPSHOT_LEADERBOARD_FT.md` |
| Tests | `backend/tests/test_first_third_range.py` |
| Live stats | `./stats.md` |

## What the outcomes record

The first-third outcome computer records:

- `oc.rest_confirms_first_third`
- `oc.rest_reverses_first_third`
- high/low break behavior
- 0.5x and 1.0x extension behavior beyond the first-third range

## ML note

The snapshot matrix uses the first-third window close as the feature cutoff. This keeps the model from seeing the rest of the period before it happens.
