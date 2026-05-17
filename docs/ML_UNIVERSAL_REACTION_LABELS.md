# Universal Reaction Labels

_Updated 2026-05-16._

## Purpose

The database should let different concepts answer the same forward-reaction questions. A gap, ITR range, macro pre-release range, FVG, sweep level, or VP level should all be able to say whether price respected, swept, rejected, held, expanded, or reversed.

The shared helper lives at `backend/app/research/outcomes/reaction_labels.py`.

## Current Coverage

| Concept | Status | Outcome version |
|---|---|---|
| Universal opening-gap level table | NDOG/NWOG at `data/ml/levels/opening_gap_level_reactions.parquet` | `level_reactions_v1` |
| Universal FVG level table | Fair-value-gap zones at `data/ml/levels/fvg_level_reactions.parquet` | `level_reactions_v1` |
| Scheduled macro events | Already has equivalent v2 labels | `v2` |
| Opening gaps / NDOG/NWOG | Uses shared helper | `v2` |
| Interval true range | Uses shared helper | `v2` |
| FVG formation | Uses shared helper for zone reaction labels | `v3` |
| Liquidity sweeps | Uses shared helper for swept-reference and manipulation-range reactions | `v2` |
| Forming volume profile | Uses shared helper for live profile-so-far reactions | `v2` |
| Completed volume profile | Has strict v2 post-touch level labels; not changed in this pass | `v2` |

## Standard Label Families

The newer wide level-reaction artifacts use:

- `level.*` for what the level was at creation time.
- `lr.<horizon>.*` for future reaction labels.

Standard clock-time horizons:

```text
next_60m
next_240m
next_1d
next_5d
next_20d
full_horizon
```

Native-bar horizons, used when the source concept is natively candle-based:

```text
next_3_bars
next_10_bars
next_50_bars
```

Core `lr.*` fields:

```text
touched
meaningful_touch
partial_touch
midpoint_touched
full_touch
closed_inside
closed_through
directional_rejection
directional_break_acceptance
continuation_acceptance
through_acceptance
partial_touch_rejected
full_touch_rejected_inside
clean_fill_through
unfilled_expanded_away
unfilled_clean_continuation
time_to_touch_minutes
time_to_meaningful_touch_minutes
time_to_full_touch_minutes
reaction_away_pts
reaction_through_pts
reaction_away_x_size
reaction_through_x_size
```

The older nested outcome families still exist and are listed below.

| Family | Example | Meaning |
|---|---|---|
| Range expansion | `range_expanded_2x_interval` | Forward window range was at least 2x the anchor range. |
| Took high/low | `took_gap_high` | Forward high traded beyond the anchor high. |
| One-sided take | `one_sided_took_interval_low` | Took one side but not the other. |
| Held side | `took_gap_high_held_above` | Took high and closed above the anchor high. |
| Rejected inside | `took_interval_low_rejected_inside` | Took low but closed back inside the anchor range. |
| Swept both | `swept_both_gap_sides` | Took both anchor high and low. |
| Swept close location | `swept_both_interval_closed_inside` | Swept both sides and finished inside the range. |
| First-bar reversal | `first_bar_up_then_final_down` | First bar moved up from reference, but final close ended below reference. |
| Reference wick/close | `wicked_above_ref_closed_below_ref` | Traded above reference, then closed below it. |

## Naming Rule

Use the anchor prefix in the label name:

| Anchor | Prefix | Example |
|---|---|---|
| Opening gap zone | `gap` | `label.next_240m.closed_inside_gap_range` |
| ITR anchor range | `interval` | `label.next_interval.range_expanded_2x_interval` |
| Macro pre-release range | `pre_15m`, `pre_60m` | `label.next_15m.took_pre_60m_high_rejected_inside` |
| FVG zone | `fvg` | `label.zone_reaction.took_fvg_high_rejected_inside` |
| Sweep manipulation range | `manipulation` | `label.manipulation_range_reaction.closed_inside_manipulation_range` |
| Forming VP profile-so-far range | `profile_so_far` | `label.next_60m.range_expanded_1x_profile_so_far` |

## Safety Rule

These are future labels. They must stay under `oc.*` in detector matrices and `label.*` in snapshot matrices. They are not model inputs.

The safe model inputs are event-time columns (`ed.*`), timestamp context (`ts.*`), and zero-look-ahead context columns (`xd.*`, `xctx.*`, `gapctx.*`) that are known before or at `asof.feature_cutoff_ts`.
