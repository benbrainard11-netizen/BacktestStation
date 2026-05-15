# Opening Gap Final Context Results

_Generated `2026-05-15T04:01:33.590967+00:00`._

This tests opening-gap anchors after adding the final context stack:
`xctx + gapctx + obgeom + liqgeom + regime`.

## Plain-English Takeaways

- The final context stack did **not** massively change the original fill/unfilled labels. Most comparable fill labels improved only a little, usually around `+0.003` to `+0.015` mean AUC.
- The new stack found very strong range-expansion and rejection labels. Best tested row: `label.next_240m.range_expanded_2x_gap`, all sides, mean AUC `0.974`, min AUC `0.965`.
- Be careful with the biggest range-expansion labels because some have high base rates. Example: `next_1d.range_expanded_2x_gap` has base rate around `0.973`, so it is not as informative as it looks by AUC alone.
- The more interesting practical signals are the lower-base rejection labels: `next_60m.resistance_rejection_3bar` mean AUC `0.942` with base rate `0.291`, and `next_60m.support_rejection_3bar` mean AUC `0.912` with base rate `0.363`.
- Decision: opening-gap final context is worth keeping. Next step should be stricter label curation for gap reactions, not just chasing the highest AUC row.

## New Walk-Forward Results

| Snapshot | Side | Label | Folds | Rows | Base rate | Mean AUC | Min AUC | Mean top bucket |
|---|---|---|---|---|---|---|---|---|
| `at_fire` | `all` | `label.next_1d.range_expanded_2x_gap` | 5 | 4323 | 0.973 | 0.988 | 0.978 | 100.0% |
| `at_fire` | `gap_up` | `label.next_240m.range_expanded_1x_gap` | 4 | 1835 | 0.939 | 0.979 | 0.958 | 100.0% |
| `at_fire` | `all` | `label.next_240m.range_expanded_2x_gap` | 6 | 5157 | 0.901 | 0.974 | 0.965 | 100.0% |
| `at_fire` | `all` | `label.next_60m.range_expanded_2x_gap` | 6 | 5157 | 0.811 | 0.953 | 0.941 | 100.0% |
| `at_fire` | `all` | `label.next_60m.resistance_rejection_3bar` | 6 | 5157 | 0.291 | 0.942 | 0.922 | 91.0% |
| `at_fire` | `all` | `label.next_60m.support_rejection_3bar` | 6 | 5157 | 0.363 | 0.912 | 0.896 | 89.7% |
| `at_fire` | `all` | `label.next_240m.unfilled_at_window_end` | 6 | 5157 | 0.225 | 0.837 | 0.805 | 75.9% |
| `at_fire` | `all` | `label.next_240m.fully_filled` | 6 | 5157 | 0.775 | 0.837 | 0.805 | 97.5% |
| `at_fire` | `gap_down` | `label.next_240m.unfilled_at_window_end` | 6 | 2303 | 0.218 | 0.833 | 0.738 | 72.2% |
| `at_fire` | `gap_down` | `label.next_240m.fully_filled` | 6 | 2303 | 0.782 | 0.833 | 0.738 | 96.5% |
| `at_fire` | `gap_up` | `label.next_60m.fully_filled` | 6 | 2854 | 0.664 | 0.832 | 0.783 | 95.4% |
| `at_fire` | `gap_up` | `label.next_60m.unfilled_at_window_end` | 6 | 2854 | 0.336 | 0.832 | 0.783 | 84.3% |
| `at_fire` | `all` | `label.next_60m.unfilled_at_window_end` | 6 | 5157 | 0.329 | 0.827 | 0.789 | 89.1% |
| `at_fire` | `all` | `label.next_60m.fully_filled` | 6 | 5157 | 0.671 | 0.827 | 0.789 | 93.8% |
| `at_fire` | `gap_up` | `label.next_240m.unfilled_at_window_end` | 6 | 2854 | 0.227 | 0.822 | 0.734 | 68.7% |
| `at_fire` | `gap_up` | `label.next_240m.fully_filled` | 6 | 2854 | 0.773 | 0.822 | 0.734 | 98.0% |

## Comparable Old vs New Walk-Forward

Old matrix: `opening_gap_snapshots_xctx_gapctx`.
New matrix: `opening_gap_snapshots_xctx_gapctx_obgeom_liqgeom_regime`.

| Snapshot | Side | Label | Old mean AUC | New mean AUC | Delta | New min AUC | New top bucket |
|---|---|---|---|---|---|---|---|
| `at_fire` | `gap_up` | `label.next_60m.fully_filled` | 0.817 | 0.832 | 0.015 | 0.783 | 95.4% |
| `at_fire` | `gap_up` | `label.next_60m.unfilled_at_window_end` | 0.817 | 0.832 | 0.015 | 0.783 | 84.3% |
| `at_fire` | `gap_up` | `label.next_240m.unfilled_at_window_end` | 0.817 | 0.822 | 0.005 | 0.734 | 68.7% |
| `at_fire` | `gap_up` | `label.next_240m.fully_filled` | 0.817 | 0.822 | 0.005 | 0.734 | 98.0% |
| `at_fire` | `all` | `label.next_60m.unfilled_at_window_end` | 0.822 | 0.827 | 0.005 | 0.789 | 89.1% |
| `at_fire` | `all` | `label.next_60m.fully_filled` | 0.822 | 0.827 | 0.005 | 0.789 | 93.8% |
| `at_fire` | `gap_down` | `label.next_240m.unfilled_at_window_end` | 0.829 | 0.833 | 0.003 | 0.738 | 72.2% |
| `at_fire` | `gap_down` | `label.next_240m.fully_filled` | 0.829 | 0.833 | 0.003 | 0.738 | 96.5% |
| `at_fire` | `all` | `label.next_240m.unfilled_at_window_end` | 0.834 | 0.837 | 0.003 | 0.805 | 75.9% |
| `at_fire` | `all` | `label.next_240m.fully_filled` | 0.834 | 0.837 | 0.003 | 0.805 | 97.5% |

## New Static Leaderboard Top Rows

| Snapshot | Side | Label | Test base rate | Static AUC | Top bucket |
|---|---|---|---|---|---|
| `at_fire` | `gap_up` | `label.next_240m.range_expanded_1x_gap` | 0.923 | 0.996 | 100.0% |
| `at_fire` | `gap_up` | `label.next_1d.range_expanded_2x_gap` | 0.936 | 0.993 | 100.0% |
| `at_fire` | `all` | `label.next_1d.range_expanded_2x_gap` | 0.962 | 0.984 | 100.0% |
| `at_fire` | `all` | `label.next_240m.range_expanded_1x_gap` | 0.950 | 0.976 | 99.5% |
| `at_fire` | `all` | `label.next_240m.range_expanded_2x_gap` | 0.880 | 0.974 | 100.0% |
| `at_fire` | `gap_up` | `label.next_60m.range_expanded_1x_gap` | 0.891 | 0.972 | 100.0% |
| `at_fire` | `all` | `label.next_60m.range_expanded_1x_gap` | 0.922 | 0.970 | 100.0% |
| `at_fire` | `gap_down` | `label.next_240m.range_expanded_2x_gap` | 0.906 | 0.963 | 100.0% |
| `at_fire` | `gap_up` | `label.next_240m.range_expanded_2x_gap` | 0.859 | 0.961 | 100.0% |
| `at_fire` | `gap_up` | `label.next_60m.range_expanded_2x_gap` | 0.753 | 0.959 | 100.0% |
| `at_fire` | `all` | `label.next_60m.range_expanded_2x_gap` | 0.783 | 0.957 | 100.0% |
| `at_fire` | `gap_down` | `label.next_60m.range_expanded_2x_gap` | 0.821 | 0.952 | 100.0% |
| `at_fire` | `all` | `label.full_horizon.resistance_rejection_3bar` | 0.270 | 0.932 | 88.2% |
| `at_fire` | `all` | `label.next_60m.resistance_rejection_3bar` | 0.270 | 0.932 | 88.2% |
| `at_fire` | `all` | `label.next_240m.resistance_rejection_3bar` | 0.270 | 0.932 | 88.2% |
| `at_fire` | `all` | `label.next_1d.resistance_rejection_3bar` | 0.270 | 0.932 | 88.2% |
| `at_fire` | `all` | `label.next_5d.resistance_rejection_3bar` | 0.270 | 0.932 | 88.2% |
| `at_fire` | `all` | `label.next_20d.resistance_rejection_3bar` | 0.270 | 0.932 | 88.2% |
| `at_fire` | `all` | `label.full_horizon.support_rejection_3bar` | 0.367 | 0.920 | 94.6% |
| `at_fire` | `all` | `label.next_60m.support_rejection_3bar` | 0.367 | 0.920 | 94.6% |
| `at_fire` | `all` | `label.next_240m.support_rejection_3bar` | 0.367 | 0.920 | 94.6% |
| `at_fire` | `all` | `label.next_1d.support_rejection_3bar` | 0.367 | 0.920 | 94.6% |
| `at_fire` | `all` | `label.next_5d.support_rejection_3bar` | 0.367 | 0.920 | 94.6% |
| `at_fire` | `all` | `label.next_20d.support_rejection_3bar` | 0.367 | 0.920 | 94.6% |
| `at_fire` | `gap_down` | `label.next_60m.range_expanded_1x_gap` | 0.961 | 0.917 | 100.0% |

## Top Feature-Family Usage In Static Top Rows

This is diagnostic only. It counts feature prefixes mentioned in `top_features` text.

| Prefix | Count |
|---|---|
| `xctx` | 83 |
| `regime` | 82 |
| `ogap` | 69 |
| `liqgeom` | 8 |
| `ts` | 6 |
| `obgeom` | 2 |

## Interpretation

- Fill/no-fill prediction was already good from `gapctx`; adding OB/liquidity/regime mostly gives small gains there.
- Reaction-style labels are where the final stack looks more useful.
- The high-base range-expansion labels should be treated as context/regime labels, not direct strategy labels.
- The lower-base rejection/acceptance labels deserve the next round of stricter testing.
