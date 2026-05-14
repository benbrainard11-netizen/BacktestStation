# Universal Reaction Labels

_Generated 2026-05-14._

## Purpose

The database should let different concepts answer the same forward-reaction questions. A gap, ITR range, macro pre-release range, FVG, sweep level, or VP level should all be able to say whether price respected, swept, rejected, held, expanded, or reversed.

The shared helper lives at `backend/app/research/outcomes/reaction_labels.py`.

## Current Coverage

| Concept | Status | Outcome version |
|---|---|---|
| Scheduled macro events | Already has equivalent v2 labels | `v2` |
| Opening gaps / NDOG/NWOG | Uses shared helper | `v2` |
| Interval true range | Uses shared helper | `v2` |
| FVG, sweeps, VP/forming VP | Next expansion target | Existing versions |

## Standard Label Families

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

## Safety Rule

These are future labels. They must stay under `oc.*` in detector matrices and `label.*` in snapshot matrices. They are not model inputs.

The safe model inputs are event-time columns (`ed.*`), timestamp context (`ts.*`), and zero-look-ahead context columns (`xd.*`, `xctx.*`, `gapctx.*`) that are known before or at `asof.feature_cutoff_ts`.
