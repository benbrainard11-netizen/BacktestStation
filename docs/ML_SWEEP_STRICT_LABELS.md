# Sweep Strict Labels

_Generated `2026-05-15T20:05:33.064017+00:00`._

These labels add strict clock-time liquidity-sweep reaction targets.
They are appended to `label_columns` only. They are not features.

Direction rule: high sweeps reject down; low sweeps reject up.

## Definitions

| Pattern | Meaning |
|---|---|
| `label.strict.<window>.sweep_failed_recovered` | Price closed back through the swept reference and ended the window on the rejection-thesis side. |
| `label.strict.<window>.sweep_succeeded_held_rejection` | Price recovered the swept reference, held the manipulation extreme, and moved at least 1x sweep depth in the rejection thesis. |
| `label.strict.<window>.sweep_partial_retest_rejected` | After recovery, price retested the swept level without taking the manipulation extreme, then rejected in the thesis direction. |
| `label.strict.<window>.sweep_failed_immediately` | Within the first minutes after the sweep, price extended past the manipulation extreme without immediate recovery. |
| `label.strict.<window>.sweep_extended_continuation` | Price did not recover the swept level and extended at least 0.5x sweep depth in the continuation direction. |

## Generated Columns

- Strict label columns: `10`
- Windows: `next_60m, next_240m`

## Coverage

| Window | Rows | Missing bar windows |
|---|---|---|
| next_60m | 52946 | 202 |
| next_240m | 52946 | 194 |

## Overall Rates

| Label | Rows | Positives | Rate |
|---|---|---|---|
| `label.strict.next_240m.sweep_extended_continuation` | 52946 | 6225 | 11.8% |
| `label.strict.next_240m.sweep_failed_immediately` | 52946 | 10096 | 19.1% |
| `label.strict.next_240m.sweep_failed_recovered` | 52946 | 13937 | 26.3% |
| `label.strict.next_240m.sweep_partial_retest_rejected` | 52946 | 5083 | 9.6% |
| `label.strict.next_240m.sweep_succeeded_held_rejection` | 52946 | 9532 | 18.0% |
| `label.strict.next_60m.sweep_extended_continuation` | 52946 | 3537 | 6.7% |
| `label.strict.next_60m.sweep_failed_immediately` | 52946 | 10084 | 19.0% |
| `label.strict.next_60m.sweep_failed_recovered` | 52946 | 12917 | 24.4% |
| `label.strict.next_60m.sweep_partial_retest_rejected` | 52946 | 3095 | 5.8% |
| `label.strict.next_60m.sweep_succeeded_held_rejection` | 52946 | 7669 | 14.5% |
