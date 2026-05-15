# Opening Gap Strict Label Results

_Generated `2026-05-15T13:28:00.167153+00:00`._

This pass derives stricter opening-gap reaction labels from existing future outcome columns and tests them on the final context matrix.

## Plain-English Takeaways

- This was worth doing because the stricter labels are more realistic than broad range-expansion labels.
- Best robust strict target: `label.strict.next_240m.partial_touch_rejected` across all gaps.
- That target got mean walk-forward AUC `0.837`, min fold AUC `0.805`, base rate `22.5%`, and top-bucket rate `75.9%`.
- The 60-minute partial-touch rejection labels also look good: around `0.826` to `0.830` mean AUC with stronger top buckets.
- Some labels were too strict and produced zero positives. That is fine; they should not be modeled until redefined.
- Compared with high-base range-expansion labels, these are cleaner research targets for actual gap behavior.

## Walk-Forward Results

| Snapshot | Side | Label | Folds | Rows | Base rate | Mean AUC | Min AUC | Top bucket | Top lift |
|---|---|---|---|---|---|---|---|---|---|
| `at_fire` | `all` | `label.strict.next_240m.partial_touch_rejected` | 6 | 5157 | 22.5% | 0.837 | 0.805 | 75.9% | 53.4% |
| `at_fire` | `gap_down` | `label.strict.next_240m.partial_touch_rejected` | 6 | 2303 | 21.8% | 0.833 | 0.738 | 72.2% | 50.4% |
| `at_fire` | `gap_up` | `label.strict.next_60m.partial_touch_rejected` | 6 | 2854 | 33.6% | 0.830 | 0.777 | 83.9% | 50.3% |
| `at_fire` | `all` | `label.strict.next_60m.partial_touch_rejected` | 6 | 5157 | 32.9% | 0.826 | 0.792 | 89.9% | 57.0% |
| `at_fire` | `all` | `label.strict.next_1d.partial_touch_rejected` | 6 | 5157 | 9.3% | 0.825 | 0.791 | 40.5% | 31.2% |
| `at_fire` | `gap_up` | `label.strict.next_240m.partial_touch_rejected` | 6 | 2854 | 22.7% | 0.822 | 0.734 | 68.7% | 46.0% |
| `at_fire` | `gap_down` | `label.strict.next_60m.partial_touch_rejected` | 6 | 2303 | 31.5% | 0.820 | 0.753 | 89.0% | 57.5% |
| `at_fire` | `gap_up` | `label.strict.next_1d.partial_touch_rejected` | 6 | 2854 | 10.2% | 0.787 | 0.736 | 36.3% | 26.1% |
| `at_fire` | `all` | `label.strict.next_1d.filled_then_continued_through` | 6 | 5157 | 87.7% | 0.762 | 0.731 | 96.0% | 8.3% |
| `at_fire` | `all` | `label.strict.next_1d.failed_fill_expanded_away` | 6 | 5157 | 7.8% | 0.750 | 0.708 | 15.9% | 8.1% |
| `at_fire` | `gap_up` | `label.strict.next_1d.filled_then_continued_through` | 6 | 2854 | 86.6% | 0.740 | 0.661 | 97.9% | 11.3% |
| `at_fire` | `gap_up` | `label.strict.next_240m.filled_then_continued_through` | 6 | 2854 | 67.5% | 0.738 | 0.660 | 86.7% | 19.3% |

## Static Leaderboard Top Rows

| Snapshot | Side | Label | Base rate | AUC | Top bucket |
|---|---|---|---|---|---|
| `at_fire` | `gap_up` | `label.strict.next_60m.partial_touch_rejected` | 37.1% | 0.872 | 96.2% |
| `at_fire` | `gap_up` | `label.strict.next_240m.partial_touch_rejected` | 27.3% | 0.856 | 92.3% |
| `at_fire` | `all` | `label.strict.next_1d.partial_touch_rejected` | 9.8% | 0.849 | 44.6% |
| `at_fire` | `all` | `label.strict.next_240m.partial_touch_rejected` | 23.7% | 0.846 | 81.2% |
| `at_fire` | `all` | `label.strict.next_60m.partial_touch_rejected` | 32.7% | 0.836 | 89.2% |
| `at_fire` | `gap_down` | `label.strict.next_240m.partial_touch_rejected` | 19.1% | 0.828 | 71.1% |
| `at_fire` | `gap_up` | `label.strict.next_1d.partial_touch_rejected` | 13.5% | 0.822 | 51.9% |
| `at_fire` | `gap_down` | `label.strict.next_60m.partial_touch_rejected` | 27.1% | 0.805 | 80.7% |
| `at_fire` | `gap_up` | `label.strict.next_1d.filled_then_continued_through` | 83.5% | 0.786 | 96.2% |
| `at_fire` | `all` | `label.strict.next_1d.filled_then_continued_through` | 87.4% | 0.783 | 95.7% |
| `at_fire` | `gap_up` | `label.strict.next_240m.filled_then_continued_through` | 62.6% | 0.779 | 86.5% |
| `at_fire` | `all` | `label.strict.next_1d.failed_fill_expanded_away` | 7.6% | 0.777 | 23.7% |
| `at_fire` | `gap_up` | `label.strict.next_60m.filled_then_continued_through` | 47.0% | 0.754 | 71.2% |
| `at_fire` | `gap_down` | `label.strict.next_240m.midpoint_hold_rejection` | 8.6% | 0.751 | 22.9% |
| `at_fire` | `all` | `label.strict.next_240m.filled_then_continued_through` | 65.9% | 0.745 | 84.4% |
| `at_fire` | `gap_down` | `label.strict.next_1d.partial_touch_rejected` | 5.2% | 0.745 | 18.1% |
| `at_fire` | `all` | `label.strict.next_240m.failed_fill_expanded_away` | 16.7% | 0.740 | 44.6% |
| `at_fire` | `gap_up` | `label.strict.next_60m.gap_held_rejection` | 65.9% | 0.737 | 98.1% |
| `at_fire` | `gap_up` | `label.strict.next_240m.gap_held_rejection` | 65.9% | 0.737 | 98.1% |
| `at_fire` | `gap_up` | `label.strict.next_1d.gap_held_rejection` | 65.9% | 0.737 | 98.1% |

## Strict Label Rates

| Label | Positives | Rate |
|---|---|---|
| `label.strict.next_1d.filled_then_continued_through` | 8271 | 87.6% |
| `label.strict.next_240m.gap_held_rejection` | 6236 | 66.1% |
| `label.strict.next_60m.gap_held_rejection` | 6236 | 66.1% |
| `label.strict.next_1d.gap_held_rejection` | 6236 | 66.1% |
| `label.strict.next_240m.filled_then_continued_through` | 6231 | 66.0% |
| `label.strict.next_60m.filled_then_continued_through` | 4533 | 48.0% |
| `label.strict.next_60m.partial_touch_rejected` | 3158 | 33.5% |
| `label.strict.next_240m.partial_touch_rejected` | 2180 | 23.1% |
| `label.strict.next_60m.failed_fill_expanded_away` | 2082 | 22.1% |
| `label.strict.next_240m.failed_fill_expanded_away` | 1562 | 16.6% |
| `label.strict.next_60m.gap_failed_acceptance` | 1449 | 15.4% |
| `label.strict.next_240m.gap_failed_acceptance` | 1449 | 15.4% |
| `label.strict.next_1d.gap_failed_acceptance` | 1449 | 15.4% |
| `label.strict.next_60m.midpoint_hold_rejection` | 1202 | 12.7% |
| `label.strict.next_1d.partial_touch_rejected` | 873 | 9.2% |
| `label.strict.next_240m.midpoint_hold_rejection` | 851 | 9.0% |
| `label.strict.next_1d.failed_fill_expanded_away` | 735 | 7.8% |
| `label.strict.next_1d.midpoint_hold_rejection` | 339 | 3.6% |
| `label.strict.next_60m.filled_then_rejected_inside` | 315 | 3.3% |
| `label.strict.next_240m.filled_then_rejected_inside` | 116 | 1.2% |
| `label.strict.next_1d.filled_then_rejected_inside` | 14 | 0.1% |
| `label.strict.next_60m.no_touch_expanded_away` | 0 | 0.0% |
| `label.strict.next_60m.clean_gap_continuation` | 0 | 0.0% |
| `label.strict.next_240m.clean_gap_continuation` | 0 | 0.0% |
| `label.strict.next_240m.no_touch_expanded_away` | 0 | 0.0% |
| `label.strict.next_1d.no_touch_expanded_away` | 0 | 0.0% |
| `label.strict.next_1d.clean_gap_continuation` | 0 | 0.0% |

## Too-Strict / Zero-Positive Labels

- `label.strict.next_60m.no_touch_expanded_away`
- `label.strict.next_60m.clean_gap_continuation`
- `label.strict.next_240m.clean_gap_continuation`
- `label.strict.next_240m.no_touch_expanded_away`
- `label.strict.next_1d.no_touch_expanded_away`
- `label.strict.next_1d.clean_gap_continuation`

## Decision

- Keep `partial_touch_rejected` as the main strict opening-gap target family.
- Keep `failed_fill_expanded_away` as a secondary low-base target, but it needs more tests.
- Drop or redefine no-touch continuation labels because this version produced no positives.
- This matrix is a good candidate for the GPU PC after it finishes sweep training.
