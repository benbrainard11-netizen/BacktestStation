# Opening Gap Strict Label Results

_Generated `2026-05-15T17:45:00+00:00`._

This pass fixes the impossible opening-gap `no_touch` labels and retests the strict opening-gap targets on the final context matrix.

## Plain-English Takeaways

- Opening-gap labels are now clean: no zero-positive strict labels remain.
- The old no-touch idea was wrong for this detector because every opening gap is considered touched by construction around the open.
- The replacement idea is better: ask whether the gap stayed unfilled and then continued/expanded away.
- Best robust target is still `label.strict.next_240m.partial_touch_rejected` across all gaps.
- Best robust result: mean walk-forward AUC `0.837`, worst-year AUC `0.805`, top 10% bucket `75.9%`.
- `unfilled_clean_continuation` also works well and is now usable instead of dead.

## Best Walk-Forward Rows

| Snapshot | Side | Label | Mean AUC | Min AUC | Top bucket |
|---|---|---|---|---|---|
| `at_fire` | `all` | `label.strict.next_240m.partial_touch_rejected` | 0.837 | 0.805 | 75.9% |
| `at_fire` | `gap_down` | `label.strict.next_240m.partial_touch_rejected` | 0.833 | 0.738 | 72.2% |
| `at_fire` | `gap_up` | `label.strict.next_60m.partial_touch_rejected` | 0.830 | 0.777 | 83.9% |
| `at_fire` | `all` | `label.strict.next_240m.unfilled_clean_continuation` | 0.827 | 0.798 | 68.9% |
| `at_fire` | `all` | `label.strict.next_60m.partial_touch_rejected` | 0.826 | 0.792 | 89.9% |
| `at_fire` | `all` | `label.strict.next_1d.partial_touch_rejected` | 0.825 | 0.791 | 40.5% |
| `at_fire` | `all` | `label.strict.next_1d.unfilled_clean_continuation` | 0.823 | 0.794 | 39.7% |

## Label Rate Notes

- `next_60m.partial_touch_rejected`: `33.5%` positive rate.
- `next_240m.partial_touch_rejected`: `23.1%` positive rate.
- `next_1d.partial_touch_rejected`: `9.2%` positive rate.
- `next_240m.unfilled_clean_continuation`: `22.0%` positive rate.
- `next_1d.unfilled_clean_continuation`: `9.2%` positive rate.

## Decision

- Keep `partial_touch_rejected` as the main strict opening-gap target family.
- Keep `unfilled_clean_continuation` as the replacement for the dead no-touch continuation idea.
- Use this dataset on the GPU PC before spending more local CPU time on it.
