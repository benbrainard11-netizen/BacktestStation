# Time Profile

> Time profile summarizes how a parent period forms across sub-sessions, then measures what the next period does.

## What it is

This detector classifies parent-period structure by where the high and low formed across time segments. Examples include daily session profiles, weekly profiles, and monthly profiles.

Time profile is a strong context family because it describes the completed parent period before predicting next-period behavior.

## Modes

| Mode | Meaning |
|---|---|
| `daily_3session` | daily profile using 3 session buckets |
| `daily_4session` | daily profile using 4 session buckets |
| `weekly` | weekly time profile |
| `monthly` | monthly time profile |

Sides are `bullish`, `bearish`, and `doji`.

## Where the code lives

| Component | Path |
|---|---|
| Detector | `backend/app/research/detectors/time_profile.py` |
| Outcomes | `backend/app/research/outcomes/time_profile_reactions.py` |
| Feature matrix | `data/ml/features/tp.parquet` |
| Snapshot matrix | `data/ml/anchors/tp_snapshots.parquet` |
| Snapshot leaderboard | `docs/ML_SNAPSHOT_LEADERBOARD_TP.md` |
| Tests | `backend/tests/test_time_profile.py` |
| Live stats | `./stats.md` |

## What the outcomes record

The time-profile outcome computer records next-period and N+2 behavior:

- `oc.next_period.took_parent_high`
- `oc.next_period.took_parent_low`
- `oc.next_period.thesis_confirmed`
- equivalent `oc.n_plus_2.*` labels

## ML note

Time profile is one of the better practical standalone context features. It should be included early in the unified cross-concept training table.
