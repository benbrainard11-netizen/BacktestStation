# VP V2 Labels

_Generated 2026-05-12._

## Current VP Semantics

The existing `volume_profile` detector builds completed-period profiles:

- Daily VP is knowable after the Globex day ends.
- Weekly VP is knowable after the Globex week ends.
- Asia/London/NY session VP is knowable after that session ends.

That is safe for completed-period research. It is not a live forming VP feed. A live feed needs a separate as-of builder that recomputes VP/VWAP only up to the current timestamp.

## What Changed

`volume_profile_reactions_v2` emits stricter reaction labels for each VP/VWAP level while preserving the old broad labels.

Old broad labels answered:

- Did the forward window wick above the level?
- Did it wick below the level?
- Did it close above the level at least once?
- Did it close below the level at least once?

New stricter labels answer:

- How many bars until first touch?
- Did first touch come from above or below?
- Did price hold above the level for 3 bars after touch?
- Did price hold below the level for 3 bars after touch?
- Did price accept above the level with 3 consecutive closes?
- Did price accept below the level with 3 consecutive closes?
- Did the level act like support rejection?
- Did the level act like resistance rejection?
- Did support break and accept below?
- Did resistance break and accept above?

These labels are designed to be harder than the old touch labels, which were often too easy and had very high base rates.

## New Label Names

For each level block such as `poc_touch`, `vah_touch`, `val_touch`, `vwap_touch`, `vwap_1sd_high_touch`, `vwap_1sd_low_touch`, `vwap_2sd_high_touch`, and `vwap_2sd_low_touch`, the outcome now includes:

- `first_touch_bars`
- `first_touch_from_above`
- `first_touch_from_below`
- `held_above_3bar_after_touch`
- `held_below_3bar_after_touch`
- `accepted_above_3bar`
- `accepted_below_3bar`
- `support_rejection_3bar`
- `resistance_rejection_3bar`
- `support_break_acceptance_3bar`
- `resistance_break_acceptance_3bar`

After outcome backfill and feature-matrix rebuild, these flatten into labels like:

- `label.vwap_touch.accepted_above_3bar`
- `label.vah_touch.resistance_rejection_3bar`
- `label.val_touch.support_rejection_3bar`
- `label.poc_touch.first_touch_from_above`

## Current Artifact Status

The stricter labels have been backfilled into the research database and rebuilt into the ML artifacts:

- Outcome backfill: `34,356` updated VP events, `1,739` skipped for missing forward data, `0` errors.
- Feature matrix: `data/ml/features/vp.parquet`, `36,095` rows.
- Snapshot matrix: `data/ml/anchors/vp_snapshots_xctx.parquet`, `36,095` rows x `808` columns.
- Audit: `docs/ML_SNAPSHOT_AUDIT_VP_V2_XCTX.md`, `0` issues and `0` warnings.
- Leaderboard: `docs/ML_SNAPSHOT_LEADERBOARD_VP_V2_XCTX.md`.
- Walk-forward: `docs/ML_SNAPSHOT_WALK_FORWARD_VP_V2_XCTX.md`.

Best current walk-forward result among the targeted strict labels:

- `at_fire / buying / label.vah_touch.resistance_break_acceptance_3bar`
- mean AUC: `0.911`
- minimum yearly AUC: `0.886`
- mean top-10% hit rate: `23.3%`
- test years: `2020` through `2025`

## Forming VP Follow-Up

The separate live-style build should be named differently, for example `forming_volume_profile` or `vp_asof`.

That build should create as-of snapshots such as:

- session VP as of every 5/15/30 minutes
- daily VP as of each hour or session boundary
- weekly VP as of current day/session

The rule is strict: no final period high, low, close, POC, VAH, VAL, or VWAP may be used unless that bar already happened before the snapshot cutoff.

## Key Files

- Outcome computer: `backend/app/research/outcomes/volume_profile_reactions.py`
- Tests: `backend/tests/test_volume_profile_reactions.py`
