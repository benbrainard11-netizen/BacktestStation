# Order Block Strict Labels

_Generated `2026-05-16T16:58:43.268313+00:00`._

These labels add strict clock-time order-block reaction targets.
They are appended to `label_columns` only. They are not features.

Direction rule: bullish/demand OBs reject up; bearish/supply OBs reject down.

## Definitions

| Pattern | Meaning |
|---|---|
| `label.strict.<window>.ob_respected_partial_test` | Price tested the entry half of the OB body, did not close through the far body edge, and rejected in the OB thesis direction. |
| `label.strict.<window>.ob_respected_deep_test` | Price tested at least 70% into the OB body, held the far body edge on closes, and rejected in the OB thesis direction. |
| `label.strict.<window>.ob_broken_through_continuation` | Price closed through the far body edge and continued in the break direction. |
| `label.strict.<window>.ob_failed_immediately` | The OB broke through early after it became knowable, before a slower retest sequence formed. |
| `label.strict.<window>.ob_swept_and_recovered` | Price swept beyond the far OB boundary, then closed back on the OB thesis side and rejected away. |

## Generated Columns

- Strict label columns: `10`
- Windows: `next_60m, next_240m`

## Coverage

| Window | Rows | Missing bar windows |
|---|---|---|
| next_60m | 46331 | 456 |
| next_240m | 46331 | 440 |

## Overall Rates

| Label | Rows | Positives | Rate |
|---|---|---|---|
| `label.strict.next_240m.ob_broken_through_continuation` | 46331 | 17451 | 37.7% |
| `label.strict.next_240m.ob_failed_immediately` | 46331 | 14193 | 30.6% |
| `label.strict.next_240m.ob_respected_deep_test` | 46331 | 3633 | 7.8% |
| `label.strict.next_240m.ob_respected_partial_test` | 46331 | 9029 | 19.5% |
| `label.strict.next_240m.ob_swept_and_recovered` | 46331 | 6435 | 13.9% |
| `label.strict.next_60m.ob_broken_through_continuation` | 46331 | 8455 | 18.2% |
| `label.strict.next_60m.ob_failed_immediately` | 46331 | 14058 | 30.3% |
| `label.strict.next_60m.ob_respected_deep_test` | 46331 | 2650 | 5.7% |
| `label.strict.next_60m.ob_respected_partial_test` | 46331 | 8741 | 18.9% |
| `label.strict.next_60m.ob_swept_and_recovered` | 46331 | 2382 | 5.1% |
