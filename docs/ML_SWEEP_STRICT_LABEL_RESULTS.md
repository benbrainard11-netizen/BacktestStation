# Sweep Strict Label Results

_Generated `2026-05-15T21:25:00+00:00`._

This pass adds true clock-time strict liquidity-sweep reaction labels to the final sweep context matrix.

## Plain-English Takeaways

- Strict sweep labels worked very well.
- The new matrix has `52,946` rows, `3,248` columns, and `10` new `label.strict.*` targets.
- Labels are computed from real 1-minute bars after `asof.label_start_ts`, not from native 3/10/50-candle proxy windows.
- All 10 labels landed in the intended all-side base-rate band: about `5.8%` to `26.3%`.
- Leakage audit is clean: `0` issues and `0` warnings.
- The best local strict sweep target is `label.strict.next_60m.sweep_failed_recovered`.
- High-side and low-side both validated strongly year-by-year.

## Direction Rule

- High sweep rejection thesis = down.
- Low sweep rejection thesis = up.

## Best Walk-Forward Rows

| Snapshot | Side | Label | Mean AUC | Min AUC | Top bucket | Top lift |
|---|---|---|---|---|---|---|
| `at_fire` | `high` | `label.strict.next_60m.sweep_failed_recovered` | 0.910 | 0.903 | 77.7% | 55.8% |
| `at_fire` | `low` | `label.strict.next_60m.sweep_failed_recovered` | 0.908 | 0.904 | 81.9% | 54.8% |
| `at_fire` | `all` | `label.strict.next_60m.sweep_failed_recovered` | 0.903 | 0.895 | 77.5% | 53.3% |
| `at_fire` | `low` | `label.strict.next_60m.sweep_succeeded_held_rejection` | 0.896 | 0.882 | 55.9% | 40.5% |

## Static Leaderboard Notes

- `next_60m.sweep_failed_recovered` was the best family across all/high/low.
- Static split AUCs were around `0.903` to `0.912`.
- Static top buckets were around `80%+` for the recovery label.
- `next_60m.sweep_succeeded_held_rejection` also looked strong, around `0.886` to `0.897` AUC.
- `next_60m.sweep_partial_retest_rejected` and `next_60m.sweep_extended_continuation` are useful secondary targets, around `0.81` to `0.83` static AUC.

## Label Rate Notes

| Label | Rate |
|---|---|
| `label.strict.next_60m.sweep_failed_recovered` | 24.4% |
| `label.strict.next_60m.sweep_succeeded_held_rejection` | 14.5% |
| `label.strict.next_60m.sweep_partial_retest_rejected` | 5.8% |
| `label.strict.next_60m.sweep_failed_immediately` | 19.0% |
| `label.strict.next_60m.sweep_extended_continuation` | 6.7% |
| `label.strict.next_240m.sweep_failed_recovered` | 26.3% |
| `label.strict.next_240m.sweep_succeeded_held_rejection` | 18.0% |
| `label.strict.next_240m.sweep_partial_retest_rejected` | 9.6% |
| `label.strict.next_240m.sweep_failed_immediately` | 19.1% |
| `label.strict.next_240m.sweep_extended_continuation` | 11.8% |

## Decision

- Ship this to benpc for full GPU XGB training.
- Primary GPU label: `label.strict.next_60m.sweep_failed_recovered`.
- Secondary GPU labels: `label.strict.next_60m.sweep_succeeded_held_rejection`, `label.strict.next_60m.sweep_partial_retest_rejected`, and `label.strict.next_60m.sweep_extended_continuation`.
- Keep 240m variants, but current evidence supports the short-horizon pattern Claude noticed.
