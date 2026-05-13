# Volume Profile

> Volume profile records value area, POC, VWAP, and VWAP-band context for a completed period.

## What it is

This detector builds volume-profile levels for session, daily, and weekly periods. It records POC, VAH, VAL, VWAP, standard-deviation bands, close location, total volume, and profile classification.

VP is a strong context family. It is also connected to Pre10, which currently uses volume-profile continuation logic.

## Modes

| Mode | Meaning |
|---|---|
| `asia_volume_profile` | Asia session profile |
| `london_volume_profile` | London session profile |
| `ny_volume_profile` | New York session profile |
| `daily_volume_profile` | daily profile |
| `weekly_volume_profile` | weekly profile |

Sides are `buying`, `selling`, and `balanced`.

## Where the code lives

| Component | Path |
|---|---|
| Detector | `backend/app/research/detectors/volume_profile.py` |
| Outcomes | `backend/app/research/outcomes/volume_profile_reactions.py` |
| Feature matrix | `data/ml/features/vp.parquet` |
| Snapshot matrix | `data/ml/anchors/vp_snapshots.parquet` |
| Snapshot leaderboard | `docs/ML_SNAPSHOT_LEADERBOARD_VP.md` |
| Tests | `backend/tests/test_volume_profile_detector.py` |
| Live stats | `./stats.md` |

## What the outcomes record

The VP outcome computer records:

- touch/close behavior around POC, VAH, VAL, VWAP, and VWAP bands
- `oc.took_period_high`
- `oc.took_period_low`
- `oc.forward_close_above_vah`
- `oc.forward_close_below_val`
- `oc.forward_close_in_value_area`

## ML note

VP has very strong ranking signal, but some profile-touch labels are too easy because their base rates are very high. Future work should focus on harder labels and cleaner horizons.
