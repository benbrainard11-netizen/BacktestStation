# FVG Strict Label Results

_Generated `2026-05-15T17:45:00+00:00`._

This pass adds 24 strict FVG labels to the richest current FVG context matrix and runs a narrowed local validation on four high-value labels. The full FVG grid is too heavy for this PC and should be trained on the GPU PC.

## Plain-English Takeaways

- FVG strict matrix built successfully: `209,339` rows, `2,114` columns, `24` new `label.strict.*` targets.
- Leakage audit is clean: `0` issues and `0` warnings.
- The strongest local FVG result is not a clean bounce. It is predicting failed taps.
- Best walk-forward label: `label.strict.forward_10c.after_tap_failed_1x_against`.
- That label got mean walk-forward AUC `0.717`, worst-year AUC `0.712`, and top 10% bucket `25.2%` versus base rate around `11.9%`.
- `no_touch_continuation` is also useful: mean AUC `0.715`, but worst-year AUC dropped to `0.671`, so it is less stable.
- Basic `tap_wick_rejected` is weak: mean AUC only `0.533`, so just knowing a wick tap/reject happened is not enough by itself.

## Local Walk-Forward Results

| Snapshot | Side | Label | Mean AUC | Min AUC | Top bucket |
|---|---|---|---|---|---|
| `at_fire` | `all` | `label.strict.forward_10c.after_tap_failed_1x_against` | 0.717 | 0.712 | 25.2% |
| `at_fire` | `all` | `label.strict.no_touch_continuation` | 0.715 | 0.671 | 14.0% |
| `at_fire` | `all` | `label.strict.forward_10c.after_tap_1x_clean` | 0.692 | 0.672 | 15.0% |
| `at_fire` | `all` | `label.strict.tap_wick_rejected` | 0.533 | 0.527 | 48.5% |

## Label Rate Notes

- `tap_wick_rejected`: `45.2%` positive rate. Common, but weak predictability.
- `forward_10c.after_tap_failed_1x_against`: `11.9%` positive rate. Best local predictive target.
- `forward_10c.after_tap_1x_clean`: `7.5%` positive rate. Usable, but weaker than failure prediction.
- `no_touch_continuation`: `5.2%` positive rate. Interesting, but needs full GPU validation.
- `partial_touch_rejected`: `1.4%` positive rate. Probably too rare for local CPU modeling, but keep for GPU experiments.
- `full_fill_rejected_inside`: `0.4%` positive rate. Very rare; treat as diagnostic unless GPU results say otherwise.

## Decision

- Send the full FVG strict dataset to the GPU PC.
- Primary GPU labels to try first: `forward_10c.after_tap_failed_1x_against`, `no_touch_continuation`, `forward_10c.after_tap_1x_clean`.
- Do not overvalue `tap_wick_rejected`; it is common but not very predictive.
- Run the full side/event-type grid on the stronger machine, not this one.
