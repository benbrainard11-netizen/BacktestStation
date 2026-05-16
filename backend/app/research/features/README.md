# Research Feature Dashboards

_Generated `2026-05-14T13:41:40+00:00` by `backend/scripts/refresh_dashboards.py`._

Each feature folder can have two files:

- `README.md`: stable human explanation of the concept and code locations.
- `stats.md`: generated current counts, labels, baseline rows, and snapshot leaderboard summary.

| Feature | Guide | Stats | Title | Rows | Cols | Coverage | Best AUC | Best label | Reading |
|---|---|---|---|---|---|---|---|---|---|
| `disp` | [guide](disp/README.md) | [stats](disp/stats.md) | Displacement Candle | 38,747 | 91 | 100.0% | 0.681 | `label.retracement.tapped_open` | Useful context signal, but not top-tier standalone. |
| `eql` | [guide](eql/README.md) | [stats](eql/stats.md) | Equal Levels | 60,338 | 81 | 100.0% | 0.639 | `label.take.wick_taken` | Weak-to-moderate signal. Useful as context more than as an anchor. |
| `ft` | [guide](ft/README.md) | [stats](ft/stats.md) | First-Third Range | 10,373 | 97 | 100.0% | 0.724 | `label.break_high.wick_breached` | Useful context signal, but not top-tier standalone. |
| `fvg` | [guide](fvg/README.md) | [stats](fvg/stats.md) | FVG Formation | 209,339 | 169 | 100.0% | 0.891 | `label.zone_reaction.took_fvg_high` | Strong ranking signal, but the best label is very imbalanced. Keep it, but design harder labels. |
| `itr` | [guide](itr/README.md) | [stats](itr/stats.md) | ITR - Interval True Range | 36,095 | 172 | 100.0% | 0.818 | `label.next_interval.range_expanded_2x_interval` | Good standalone signal. |
| `macro` | [guide](macro/README.md) | [stats](macro/stats.md) | Scheduled Macro Events | 18,414 | 468 | 100.0% | 0.927 | `label.next_15m.range_expanded_2x_pre_60m` | Strong ranking signal, but the best label is very imbalanced. Keep it, but design harder labels. |
| `ob` | [guide](ob/README.md) | [stats](ob/stats.md) | Order Block | 46,331 | 297 | 100.0% | 0.811 | `label.strict.next_60m.ob_swept_and_recovered` | Good standalone signal. |
| `ogap` | [guide](ogap/README.md) | [stats](ogap/stats.md) | Opening Gap Levels | 9,438 | 487 | 100.0% | 0.850 | `label.next_240m.unfilled_at_window_end` | Strong standalone signal. |
| `orb` | [guide](orb/README.md) | [stats](orb/stats.md) | Opening Range Breakout | 34,040 | 99 | 100.0% | 0.704 | `label.broke_only_low` | Useful context signal, but not top-tier standalone. |
| `psp` | [guide](psp/README.md) | [stats](psp/stats.md) | PSP Candle Divergence | 15,827 | 88 | 100.0% | 0.514 | `label.majority_reaction.all_rolled` | Weak signal in the current label setup. |
| `smt` | [guide](smt/README.md) | [stats](smt/stats.md) | SMT - HTF Reference Divergence | 2,891 | 121 | 100.0% | 0.910 | `label.n1_thesis_confirmed_strict` | Strong standalone signal. |
| `sweep` | [guide](sweep/README.md) | [stats](sweep/stats.md) | Liquidity Sweep | 52,946 | 155 | 100.0% | 0.894 | `label.ob_confirmation.did_confirm` | Strong ranking signal, but the best label is very imbalanced. Keep it, but design harder labels. |
| `swing` | [guide](swing/README.md) | [stats](swing/stats.md) | Swing Pivot | 76,786 | 73 | 100.0% | 0.805 | `label.strict.next_60m.pivot_broken_through_continuation` | Good standalone signal. |
| `tp` | [guide](tp/README.md) | [stats](tp/stats.md) | Time Profile | 19,414 | 84 | 100.0% | 0.766 | `label.next_period.took_parent_high` | Good standalone signal. |
| `vp` | [guide](vp/README.md) | [stats](vp/stats.md) | Volume Profile | 36,095 | 212 | 100.0% | 0.961 | `label.vwap_1sd_low_touch.wicked_above` | Strong ranking signal, but the best label is very imbalanced. Keep it, but design harder labels. |
| `pre10` | [guide](pre10/README.md) | [stats](pre10/stats.md) | Pre10 | 19 | 47 | - | - | - | Labeled trade outcome dataset found. |

Refresh command:

```powershell
python backend/scripts/refresh_dashboards.py all
```
