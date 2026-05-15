# Opening Gap Strict Labels

_Generated `2026-05-15T04:36:53.219325+00:00`._

These labels combine the raw opening-gap outcomes into stricter reaction targets.
They are appended to `label_columns` only. They are not features.

## Definitions

| Pattern | Meaning |
|---|---|
| `label.strict.<window>.gap_held_rejection` | Gap was touched and then acted as directional support/resistance for the 3-bar hold rule. |
| `label.strict.<window>.gap_failed_acceptance` | Gap was touched and then accepted through against the opening-gap direction. |
| `label.strict.<window>.partial_touch_rejected` | Gap was touched but not fully filled, then rejected in the directional support/resistance sense. |
| `label.strict.<window>.midpoint_hold_rejection` | Gap midpoint was touched without full fill, then held/rejected in the directional sense. |
| `label.strict.<window>.filled_then_rejected_inside` | Gap fully filled, then rejected back inside instead of accepting through. |
| `label.strict.<window>.filled_then_continued_through` | Gap fully filled and then accepted through the far side. |
| `label.strict.<window>.failed_fill_expanded_away` | Gap was touched but left unfilled, then expanded away from the gap. |
| `label.strict.<window>.no_touch_expanded_away` | Gap was never touched and price expanded away from it. |
| `label.strict.<window>.clean_gap_continuation` | No touch plus 3-bar acceptance in the opening-gap continuation direction. |

## Generated Columns

- Strict label columns: `27`
- Windows: `next_60m, next_240m, next_1d`

## Overall Rates

| Label | Rows | Positives | Rate |
|---|---|---|---|
| `label.strict.next_1d.filled_then_continued_through` | 9438 | 8271 | 87.6% |
| `label.strict.next_240m.gap_held_rejection` | 9438 | 6236 | 66.1% |
| `label.strict.next_60m.gap_held_rejection` | 9438 | 6236 | 66.1% |
| `label.strict.next_1d.gap_held_rejection` | 9438 | 6236 | 66.1% |
| `label.strict.next_240m.filled_then_continued_through` | 9438 | 6231 | 66.0% |
| `label.strict.next_60m.filled_then_continued_through` | 9438 | 4533 | 48.0% |
| `label.strict.next_60m.partial_touch_rejected` | 9438 | 3158 | 33.5% |
| `label.strict.next_240m.partial_touch_rejected` | 9438 | 2180 | 23.1% |
| `label.strict.next_60m.failed_fill_expanded_away` | 9438 | 2082 | 22.1% |
| `label.strict.next_240m.failed_fill_expanded_away` | 9438 | 1562 | 16.6% |
| `label.strict.next_60m.gap_failed_acceptance` | 9438 | 1449 | 15.4% |
| `label.strict.next_240m.gap_failed_acceptance` | 9438 | 1449 | 15.4% |
| `label.strict.next_1d.gap_failed_acceptance` | 9438 | 1449 | 15.4% |
| `label.strict.next_60m.midpoint_hold_rejection` | 9438 | 1202 | 12.7% |
| `label.strict.next_1d.partial_touch_rejected` | 9438 | 873 | 9.2% |
| `label.strict.next_240m.midpoint_hold_rejection` | 9438 | 851 | 9.0% |
| `label.strict.next_1d.failed_fill_expanded_away` | 9438 | 735 | 7.8% |
| `label.strict.next_1d.midpoint_hold_rejection` | 9438 | 339 | 3.6% |
| `label.strict.next_60m.filled_then_rejected_inside` | 9438 | 315 | 3.3% |
| `label.strict.next_240m.filled_then_rejected_inside` | 9438 | 116 | 1.2% |
| `label.strict.next_1d.filled_then_rejected_inside` | 9438 | 14 | 0.1% |
| `label.strict.next_60m.no_touch_expanded_away` | 9438 | 0 | 0.0% |
| `label.strict.next_60m.clean_gap_continuation` | 9438 | 0 | 0.0% |
| `label.strict.next_240m.clean_gap_continuation` | 9438 | 0 | 0.0% |
| `label.strict.next_240m.no_touch_expanded_away` | 9438 | 0 | 0.0% |
| `label.strict.next_1d.no_touch_expanded_away` | 9438 | 0 | 0.0% |
| `label.strict.next_1d.clean_gap_continuation` | 9438 | 0 | 0.0% |
