# Context Layer Model Results

_Generated `2026-05-15T02:12:58.588715+00:00`._

This compares the previous strongest matrices against the new context-layer matrices.

## Plain-English Takeaways

- Sweep improved most. The new sweep matrix found a stronger walk-forward target: `range_expanded_2x_manipulation` with mean AUC `0.907` and min fold AUC `0.861`.
- Sweep OB-confirmation did not materially improve. It was already strong; new context is roughly flat to slightly down on that specific label.
- SMT period-close stayed very strong, but the new layers only slightly changed the best thesis result. This means SMT already had most of that signal before the new layers.
- SMT at-fire thesis is still weak. Best at-fire clean thesis row is only mean AUC `0.560`, with a bad min fold AUC `0.462`. That is not production-grade signal.
- The new layers are useful for database richness, but we should not blindly add them everywhere. Sweep justifies further work; SMT at-fire does not yet.

## Sweep New Walk-Forward

| Snapshot | Side | Label | Folds | Mean AUC | Min AUC | Mean top bucket |
|---|---|---|---|---|---|---|
| `at_fire` | `low` | `label.manipulation_range_reaction.range_expanded_2x_manipulation` | 6 | 0.907 | 0.861 | 99.8% |
| `at_fire` | `all` | `label.manipulation_range_reaction.range_expanded_2x_manipulation` | 6 | 0.903 | 0.830 | 99.7% |
| `at_fire` | `all` | `label.ob_confirmation.did_confirm` | 6 | 0.896 | 0.856 | 100.0% |
| `at_fire` | `high` | `label.ob_confirmation.did_confirm` | 6 | 0.894 | 0.873 | 99.9% |
| `at_fire` | `high` | `label.manipulation_range_reaction.range_expanded_2x_manipulation` | 6 | 0.887 | 0.800 | 99.8% |
| `at_fire` | `low` | `label.ob_confirmation.did_confirm` | 6 | 0.863 | 0.782 | 100.0% |
| `at_fire` | `high` | `label.swept_reference_reaction.first_bar_down_then_final_up` | 6 | 0.823 | 0.803 | 33.7% |
| `at_fire` | `high` | `label.swept_level_recovery.level_recovered` | 6 | 0.792 | 0.747 | 95.2% |

## Sweep Walk-Forward Delta Where Comparable

Positive means the new final matrix beat the previous `xctx_fvggeom_obgeom` matrix.

| Snapshot | Side | Label | Old mean AUC | New mean AUC | Delta |
|---|---|---|---|---|---|
| `at_fire` | `high` | `label.swept_level_recovery.level_recovered` | 0.775 | 0.792 | 0.018 |
| `at_fire` | `low` | `label.ob_confirmation.did_confirm` | 0.864 | 0.863 | -0.001 |
| `at_fire` | `all` | `label.ob_confirmation.did_confirm` | 0.897 | 0.896 | -0.002 |
| `at_fire` | `high` | `label.ob_confirmation.did_confirm` | 0.898 | 0.894 | -0.004 |

## Sweep Static AUC Biggest Matched Gains

| Snapshot | Side | Label | Old AUC | New AUC | Delta |
|---|---|---|---|---|---|
| `at_fire` | `high` | `label.swept_reference_reaction.close_below_reference` | 0.540 | 0.622 | 0.082 |
| `at_fire` | `low` | `label.forward_continuation.continued` | 0.638 | 0.700 | 0.061 |
| `at_fire` | `high` | `label.swept_reference_reaction.wicked_above_ref_closed_below_ref` | 0.538 | 0.595 | 0.057 |
| `at_fire` | `low` | `label.manipulation_range_reaction.took_manipulation_low` | 0.633 | 0.687 | 0.054 |
| `at_fire` | `all` | `label.swept_reference_reaction.close_above_reference` | 0.599 | 0.650 | 0.051 |
| `at_fire` | `high` | `label.swept_reference_reaction.close_above_reference` | 0.558 | 0.609 | 0.051 |
| `at_fire` | `high` | `label.swept_reference_reaction.direction_reversed_from_first_bar` | 0.597 | 0.645 | 0.048 |
| `at_fire` | `low` | `label.swept_reference_reaction.wicked_below_ref_closed_above_ref` | 0.585 | 0.628 | 0.043 |
| `at_fire` | `all` | `label.swept_reference_reaction.close_below_reference` | 0.610 | 0.650 | 0.040 |
| `at_fire` | `low` | `label.manipulation_range_reaction.one_sided_took_manipulation_high` | 0.639 | 0.677 | 0.039 |
| `at_fire` | `low` | `label.swept_reference_reaction.close_below_reference` | 0.601 | 0.640 | 0.038 |
| `at_fire` | `all` | `label.swept_reference_reaction.wicked_above_ref_closed_below_ref` | 0.568 | 0.600 | 0.033 |

## SMT New Walk-Forward: Period-Close Dominated

| Snapshot | Side | Label | Folds | Mean AUC | Min AUC | Mean top bucket |
|---|---|---|---|---|---|---|
| `at_period_close` | `high` | `label.n1_primary_took_period_n_high` | 6 | 0.975 | 0.966 | 100.0% |
| `at_period_close` | `high` | `label.n1_close_moved_with_thesis` | 6 | 0.970 | 0.953 | 98.7% |
| `at_period_close` | `high` | `label.n1_thesis_confirmed_strict` | 6 | 0.967 | 0.955 | 100.0% |
| `at_period_close` | `high` | `label.n1_primary_took_period_n_low` | 6 | 0.967 | 0.955 | 100.0% |
| `at_period_close` | `low` | `label.n1_primary_took_period_n_low` | 6 | 0.964 | 0.931 | 100.0% |
| `at_period_close` | `all` | `label.n1_primary_took_period_n_high` | 6 | 0.964 | 0.959 | 100.0% |
| `at_period_close` | `all` | `label.n1_primary_took_period_n_low` | 6 | 0.963 | 0.949 | 99.4% |
| `at_period_close` | `all` | `label.n1_close_moved_with_thesis` | 6 | 0.957 | 0.946 | 100.0% |

## SMT Walk-Forward Delta Where Comparable

| Snapshot | Side | Label | Old mean AUC | New mean AUC | Delta |
|---|---|---|---|---|---|
| `at_period_close` | `high` | `label.n1_thesis_confirmed_strict` | 0.964 | 0.967 | 0.003 |

## SMT At-Fire Clean Thesis Check

These are the live-style rows that only know what was available when SMT fired.

| Snapshot | Side | Label | Folds | Mean AUC | Min AUC | Mean top bucket |
|---|---|---|---|---|---|---|
| `at_fire` | `high` | `label.n1_thesis_confirmed_strict` | 6 | 0.560 | 0.462 | 46.1% |
| `at_fire` | `low` | `label.n1_close_moved_with_thesis` | 6 | 0.551 | 0.482 | 57.5% |
| `at_fire` | `high` | `label.n1_close_moved_with_thesis` | 6 | 0.551 | 0.443 | 39.8% |
| `at_fire` | `low` | `label.n1_thesis_confirmed_strict` | 6 | 0.527 | 0.479 | 50.0% |
| `at_fire` | `all` | `label.n1_close_moved_with_thesis` | 6 | 0.512 | 0.459 | 47.4% |
| `at_fire` | `all` | `label.n1_thesis_confirmed_strict` | 6 | 0.512 | 0.489 | 47.7% |

## SMT Static AUC Biggest Matched Gains

| Snapshot | Side | Label | Old AUC | New AUC | Delta |
|---|---|---|---|---|---|
| `at_fire` | `high` | `label.n1_or_n2_thesis_confirmed_strict` | 0.502 | 0.641 | 0.138 |
| `at_fire` | `all` | `label.n2_primary_took_period_n_high` | 0.527 | 0.642 | 0.115 |
| `at_fire` | `all` | `label.n1_primary_took_period_n_low` | 0.533 | 0.636 | 0.102 |
| `at_fire` | `high` | `label.n1_or_n2_close_moved_with_thesis` | 0.520 | 0.621 | 0.101 |
| `at_fire` | `high` | `label.n2_primary_took_period_n_high` | 0.513 | 0.613 | 0.099 |
| `at_fire` | `high` | `label.n2_primary_took_period_n_low` | 0.546 | 0.627 | 0.080 |
| `at_fire` | `high` | `label.n2_thesis_confirmed_strict` | 0.546 | 0.627 | 0.080 |
| `at_fire` | `high` | `label.n1_primary_took_period_n_high` | 0.470 | 0.549 | 0.079 |
| `at_fire` | `high` | `label.n2_close_moved_with_thesis` | 0.574 | 0.650 | 0.075 |
| `at_fire` | `low` | `label.n1_or_n2_close_moved_with_thesis` | 0.525 | 0.596 | 0.070 |
| `at_fire` | `low` | `label.n1_or_n2_thesis_confirmed_strict` | 0.541 | 0.609 | 0.069 |
| `at_fire` | `low` | `label.n2_thesis_confirmed_strict` | 0.549 | 0.616 | 0.067 |

## Top Feature-Family Usage In New Static Runs

This is a rough count from the `top_features` text across top result rows. It is diagnostic only.

### Sweep

| Prefix | Count in top-feature text |
|---|---|
| `xctx` | 96 |
| `fvggeom` | 67 |
| `regime` | 59 |
| `sweep` | 40 |
| `liqgeom` | 33 |
| `obgeom` | 4 |
| `ts` | 1 |

### SMT

| Prefix | Count in top-feature text |
|---|---|
| `fvggeom` | 168 |
| `pc` | 72 |
| `xctx` | 28 |
| `liqgeom` | 23 |
| `obgeom` | 9 |

## Decision

- Expand/further test the new context stack for sweep-like reaction labels.
- Do not treat SMT at-fire as solved. It needs better labels, better context, or a different modeling setup.
- Period-close SMT can remain in the research set, but it should be labeled as period-close confirmation research, not fire-time prediction.
- Next useful build: apply final context stack to FVG or opening-gap and run the same walk-forward comparison.
