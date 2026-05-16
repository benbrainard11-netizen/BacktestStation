# Swing Pivot Strict Labels

_Generated `2026-05-16T01:01:32.365772+00:00`._

These labels add strict clock-time swing-pivot reaction targets.
They are appended to `label_columns` only. They are not features.

Direction rule: swing highs act as resistance and reject down; swing lows act as support and reject up.

## Definitions

| Pattern | Meaning |
|---|---|
| `label.strict.<window>.pivot_held_rejection` | Price tested the pivot, did not close through it, and moved away in the rejection thesis. |
| `label.strict.<window>.pivot_broken_through_continuation` | Price closed through the pivot and continued in the break direction. |
| `label.strict.<window>.pivot_partial_test_rejected` | Price entered the pivot zone without a full touch, then rejected away from the level. |
| `label.strict.<window>.pivot_failed_immediately` | The pivot traded through early after it became knowable, before a slower retest sequence formed. |
| `label.strict.<window>.pivot_double_test_held` | Price tested the pivot in at least two separate clusters, held, and rejected after the second test. |

## Generated Columns

- Strict label columns: `10`
- Windows: `next_60m, next_240m`

## Coverage

| Window | Rows | Missing bar windows |
|---|---|---|
| next_60m | 76786 | 6185 |
| next_240m | 76786 | 5890 |

## Overall Rates

| Label | Rows | Positives | Rate |
|---|---|---|---|
| `label.strict.next_240m.pivot_broken_through_continuation` | 76786 | 14227 | 18.5% |
| `label.strict.next_240m.pivot_double_test_held` | 76786 | 12822 | 16.7% |
| `label.strict.next_240m.pivot_failed_immediately` | 76786 | 4764 | 6.2% |
| `label.strict.next_240m.pivot_held_rejection` | 76786 | 17880 | 23.3% |
| `label.strict.next_240m.pivot_partial_test_rejected` | 76786 | 16451 | 21.4% |
| `label.strict.next_60m.pivot_broken_through_continuation` | 76786 | 3904 | 5.1% |
| `label.strict.next_60m.pivot_double_test_held` | 76786 | 8596 | 11.2% |
| `label.strict.next_60m.pivot_failed_immediately` | 76786 | 4671 | 6.1% |
| `label.strict.next_60m.pivot_held_rejection` | 76786 | 17039 | 22.2% |
| `label.strict.next_60m.pivot_partial_test_rejected` | 76786 | 16151 | 21.0% |
