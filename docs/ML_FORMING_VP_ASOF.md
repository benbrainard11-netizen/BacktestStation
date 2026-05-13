# Forming VP As-Of Dataset

_Generated 2026-05-13._

## What This Is

`forming_volume_profile` is the live-style version of volume profile.

Instead of waiting for the full Globex day to close, it creates an as-of
snapshot inside the active day. The first built cadence is:

- `daily_vp_asof_4h`
- 5 snapshots per symbol per Globex day
- snapshot cutoffs at 4h, 8h, 12h, 16h, and 20h after the Globex day opens

Each row only uses 1m bars with timestamps before `ed.asof_ts_utc`.

## Why It Exists

Completed VP answers:

- "What did the finished day/session/week profile look like?"

Forming VP answers:

- "At this point in the live day, what did the profile look like so far?"
- "From that as-of state, what happened next?"

That makes this dataset closer to what a live model could actually know.

## Leakage Rule

For every forming VP row:

- Feature cutoff: `asof.feature_cutoff_ts`
- Profile input bars: `[parent_period_start_utc, asof_ts_utc)`
- Label window starts after the cutoff.
- Final day high, low, close, POC, VAH, VAL, VWAP are not used as inputs.

The audit passed with `0` issues and `0` warnings.

## Current Build

- Research events: `43,150`
- Events with v1 outcomes: `42,521`
- Skipped outcome rows: `629`, due to missing forward 1m bars around known warehouse gaps
- Feature matrix: `data/ml/features/fvp.parquet`, `43,150` rows x `493` columns
- Snapshot matrix: `data/ml/anchors/forming_vp_snapshots_xctx.parquet`, `43,150` rows x `1,133` columns
- Safe model feature columns: `710`
- Label columns: `411`
- Cross-concept context columns: `640`

## Best Current Walk-Forward Result

Best hardened row:

- `at_fire / selling / label.next_240m.vah_touch.resistance_break_acceptance_3bar`
- Mean AUC: `0.919`
- Minimum yearly AUC: `0.881`
- Mean top-10% hit rate: `13.7%`
- Test years: `2020` through `2025`

Plain English:

- In selling-shaped forming profiles, the model can identify cases where price is likely to break above the current as-of VAH and then hold/accept above it within the next 240 minutes.
- The event is rare, around a low single-digit base rate, but the model's top bucket finds it much more often than random.

Other strong results:

- `selling / next_240m VAH resistance rejection`: mean AUC `0.918`
- `selling / next_60m takes current profile high`: mean AUC `0.912`, top bucket hit rate `65.2%`
- `all / next_240m VAH resistance rejection`: mean AUC `0.904`
- `buying / next_60m VWAP resistance break acceptance`: mean AUC `0.901`

## Key Files

- Detector: `backend/app/research/detectors/forming_volume_profile.py`
- Outcome computer: `backend/app/research/outcomes/forming_volume_profile_reactions.py`
- Fast outcome backfill: `backend/scripts/backfill_forming_volume_profile_outcomes.py`
- Tests: `backend/tests/test_forming_volume_profile.py`
- Audit: `docs/ML_SNAPSHOT_AUDIT_FORMING_VP_XCTX.md`
- Leaderboard: `docs/ML_SNAPSHOT_LEADERBOARD_FORMING_VP_XCTX.md`
- Walk-forward: `docs/ML_SNAPSHOT_WALK_FORWARD_FORMING_VP_XCTX.md`
