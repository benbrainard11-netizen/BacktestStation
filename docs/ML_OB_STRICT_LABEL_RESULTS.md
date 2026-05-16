# Order Block Strict Label Results

_Generated `2026-05-16T17:05:00+00:00`._

## Scope

- Matrix: `data/ml/anchors/ob_snapshots_xctx_strict.parquet`
- Rows: `46,331`
- Feature columns: `650`
- Strict labels: `10`
- Snapshots: `at_fire`
- Audit: `0` issues, `0` warnings

## Label Health

All strict order-block labels landed in the target all-side base-rate band of `5%` to `40%`.

| Label | Base rate |
|---|---:|
| `label.strict.next_60m.ob_swept_and_recovered` | 5.1% |
| `label.strict.next_60m.ob_respected_deep_test` | 5.7% |
| `label.strict.next_240m.ob_respected_deep_test` | 7.8% |
| `label.strict.next_240m.ob_swept_and_recovered` | 13.9% |
| `label.strict.next_60m.ob_broken_through_continuation` | 18.2% |
| `label.strict.next_60m.ob_respected_partial_test` | 18.9% |
| `label.strict.next_240m.ob_respected_partial_test` | 19.5% |
| `label.strict.next_60m.ob_failed_immediately` | 30.3% |
| `label.strict.next_240m.ob_failed_immediately` | 30.6% |
| `label.strict.next_240m.ob_broken_through_continuation` | 37.7% |

## Static Leaderboard

| Rank | Side | Label | Test AUC | Top-10% rate | Lift |
|---:|---|---|---:|---:|---:|
| 1 | bullish | `label.strict.next_60m.ob_swept_and_recovered` | 0.811 | 21.3% | +15.8% |
| 2 | all | `label.strict.next_60m.ob_broken_through_continuation` | 0.803 | 57.1% | +37.7% |
| 3 | bearish | `label.strict.next_60m.ob_broken_through_continuation` | 0.803 | 59.8% | +39.2% |
| 4 | bullish | `label.strict.next_60m.ob_broken_through_continuation` | 0.792 | 55.7% | +37.6% |
| 5 | all | `label.strict.next_60m.ob_swept_and_recovered` | 0.790 | 18.7% | +13.3% |

## Walk-Forward

| Rank | Side | Label | Folds | Mean AUC | Min AUC | Mean top-10% rate | Mean lift |
|---:|---|---|---:|---:|---:|---:|---:|
| 1 | all | `label.strict.next_60m.ob_broken_through_continuation` | 6 | 0.797 | 0.772 | 55.2% | +36.5% |
| 2 | bearish | `label.strict.next_60m.ob_broken_through_continuation` | 6 | 0.794 | 0.771 | 54.3% | +34.9% |
| 3 | all | `label.strict.next_60m.ob_swept_and_recovered` | 6 | 0.793 | 0.753 | 19.7% | +14.2% |
| 4 | bullish | `label.strict.next_60m.ob_broken_through_continuation` | 6 | 0.785 | 0.744 | 53.2% | +35.1% |
| 5 | bullish | `label.strict.next_60m.ob_swept_and_recovered` | 6 | 0.781 | 0.720 | 20.6% | +15.1% |
| 6 | all | `label.strict.next_240m.ob_broken_through_continuation` | 6 | 0.770 | 0.737 | 76.6% | +38.6% |
| 7 | all | `label.strict.next_60m.ob_failed_immediately` | 6 | 0.767 | 0.756 | 62.0% | +31.3% |
| 8 | bearish | `label.strict.next_240m.ob_broken_through_continuation` | 6 | 0.766 | 0.734 | 75.7% | +36.3% |

## Read

- Best rare signal: `next_60m.ob_swept_and_recovered`. It is only about `5%` base rate, but the model top bucket finds roughly `20%`.
- Best broad signal: `next_60m.ob_broken_through_continuation`. It is less rare at about `18%` base rate, but the model ranks it very cleanly with about `55%` top-bucket hit rate in walk-forward.
- The 60m horizon is stronger than 240m for OB, matching the strict-label pattern from opening gaps and sweeps.
- Respect/partial/deep-test labels are usable, but weaker than break/continuation and swept/recovered in this first OB matrix.
- Top features are mostly OB body width, confirmation geometry, tracking timeframe, and cross-concept liquidity/FVG context. That is good: the model is not just reading label proxies.

## Files

- Definitions: `docs/ML_OB_STRICT_LABELS.md`
- Audit: `docs/ML_SNAPSHOT_AUDIT_OB_STRICT_CONTEXT.md`
- Static leaderboard: `docs/ML_SNAPSHOT_LEADERBOARD_OB_STRICT_CONTEXT.md`
- Walk-forward: `docs/ML_SNAPSHOT_WALK_FORWARD_OB_STRICT_CONTEXT.md`
