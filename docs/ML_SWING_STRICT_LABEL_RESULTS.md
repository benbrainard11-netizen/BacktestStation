# Swing Pivot Strict Label Results

_Generated `2026-05-16T01:12:00+00:00`._

## Scope

- Matrix: `data/ml/anchors/swing_snapshots_strict.parquet`
- Rows: `76,786`
- Feature columns: `37`
- Strict labels: `10`
- Snapshots: `at_fire`
- Audit: `0` issues, `0` warnings

## Label Health

All strict swing labels landed in the target all-side base-rate band of `5%` to `40%`.

| Label | Base rate |
|---|---:|
| `label.strict.next_60m.pivot_broken_through_continuation` | 5.1% |
| `label.strict.next_60m.pivot_failed_immediately` | 6.1% |
| `label.strict.next_60m.pivot_double_test_held` | 11.2% |
| `label.strict.next_60m.pivot_partial_test_rejected` | 21.0% |
| `label.strict.next_60m.pivot_held_rejection` | 22.2% |
| `label.strict.next_240m.pivot_failed_immediately` | 6.2% |
| `label.strict.next_240m.pivot_double_test_held` | 16.7% |
| `label.strict.next_240m.pivot_broken_through_continuation` | 18.5% |
| `label.strict.next_240m.pivot_partial_test_rejected` | 21.4% |
| `label.strict.next_240m.pivot_held_rejection` | 23.3% |

## Static Leaderboard

| Rank | Side | Label | Test AUC | Top-10% rate | Lift |
|---:|---|---|---:|---:|---:|
| 1 | all | `label.strict.next_60m.pivot_broken_through_continuation` | 0.805 | 18.9% | +13.7% |
| 2 | all | `label.strict.next_240m.pivot_broken_through_continuation` | 0.804 | 47.7% | +29.6% |
| 3 | low | `label.strict.next_240m.pivot_broken_through_continuation` | 0.803 | 46.6% | +28.9% |
| 4 | high | `label.strict.next_240m.pivot_broken_through_continuation` | 0.799 | 47.2% | +28.7% |
| 5 | high | `label.strict.next_60m.pivot_broken_through_continuation` | 0.799 | 18.1% | +12.7% |

## Walk-Forward

| Rank | Side | Label | Folds | Mean AUC | Min AUC | Mean top-10% rate | Mean lift |
|---:|---|---|---:|---:|---:|---:|---:|
| 1 | all | `label.strict.next_60m.pivot_broken_through_continuation` | 6 | 0.804 | 0.771 | 20.0% | +14.7% |
| 2 | high | `label.strict.next_60m.pivot_broken_through_continuation` | 6 | 0.796 | 0.759 | 18.1% | +12.6% |
| 3 | all | `label.strict.next_240m.pivot_broken_through_continuation` | 6 | 0.792 | 0.736 | 48.1% | +29.1% |
| 4 | low | `label.strict.next_240m.pivot_broken_through_continuation` | 6 | 0.790 | 0.750 | 47.4% | +29.4% |
| 5 | low | `label.strict.next_60m.pivot_broken_through_continuation` | 6 | 0.788 | 0.754 | 17.3% | +12.1% |
| 6 | high | `label.strict.next_240m.pivot_broken_through_continuation` | 6 | 0.785 | 0.714 | 47.5% | +27.7% |
| 7 | all | `label.strict.next_60m.pivot_failed_immediately` | 6 | 0.775 | 0.747 | 20.6% | +14.1% |
| 8 | low | `label.strict.next_60m.pivot_failed_immediately` | 6 | 0.775 | 0.739 | 19.7% | +13.6% |

## Read

- Best signal: pivot break/continuation, especially `next_60m`.
- Best practical target: `next_60m.pivot_broken_through_continuation` because the base rate is only about `5%`, but the model's top bucket finds about `20%`.
- `next_240m.pivot_broken_through_continuation` has a higher top-bucket hit rate, but its base rate is also much higher, so the lift is less rare-signal-like.
- Held/rejection and partial-test labels are usable, but weaker than break/continuation in this first matrix.
- Top features are mostly time-of-day, tracking timeframe, event type, and pivot price. That means swing pivots currently behave more like timing/structure context than a rich geometry model.

## Files

- Definitions: `docs/ML_SWING_STRICT_LABELS.md`
- Audit: `docs/ML_SNAPSHOT_AUDIT_SWING_STRICT_CONTEXT.md`
- Static leaderboard: `docs/ML_SNAPSHOT_LEADERBOARD_SWING_STRICT_CONTEXT.md`
- Walk-forward: `docs/ML_SNAPSHOT_WALK_FORWARD_SWING_STRICT_CONTEXT.md`
