# ML Safety Audit

_Generated `2026-05-17T13:32:06.139664+00:00`._

Status: `PASS`

## Rule

- `oc.*`, `label.*`, and `lr.*` are future/outcome columns.
- They can be used as target labels or diagnostics.
- They must not be fed as normal model input features.

## Snapshot Schema Checks

| Schema | Rows | Features | Labels | Forbidden features | Feature/label overlap |
|---|---|---|---|---|---|
| `disp_snapshots` | 38,747 | 44 | 33 | 0 | 0 |
| `eql_snapshots` | 60,338 | 39 | 38 | 0 | 0 |
| `forming_vp_snapshots` | 43,150 | 73 | 507 | 0 | 0 |
| `forming_vp_snapshots_xctx` | 43,150 | 869 | 507 | 0 | 0 |
| `forming_vp_snapshots_xctx_gapctx` | 43,150 | 1,067 | 507 | 0 | 0 |
| `forming_vp_snapshots_xctx_gapctx_obgeom` | 43,150 | 1,728 | 507 | 0 | 0 |
| `ft_snapshots` | 10,373 | 40 | 37 | 0 | 0 |
| `fvg_snapshots` | 209,339 | 49 | 109 | 0 | 0 |
| `fvg_snapshots_xctx` | 209,339 | 857 | 109 | 0 | 0 |
| `fvg_snapshots_xctx_fvggeom` | 209,339 | 1,308 | 109 | 0 | 0 |
| `fvg_snapshots_xctx_fvggeom_obgeom` | 209,339 | 1,969 | 109 | 0 | 0 |
| `fvg_snapshots_xctx_fvggeom_obgeom_strict` | 209,339 | 1,969 | 133 | 0 | 0 |
| `itr_snapshots` | 36,095 | 103 | 59 | 0 | 0 |
| `itr_snapshots_xctx` | 36,095 | 899 | 59 | 0 | 0 |
| `macro_event_snapshots` | 18,414 | 70 | 372 | 0 | 0 |
| `macro_event_snapshots_xctx` | 18,414 | 878 | 372 | 0 | 0 |
| `ob_snapshots` | 46,331 | 58 | 226 | 0 | 0 |
| `ob_snapshots_xctx` | 46,331 | 650 | 226 | 0 | 0 |
| `ob_snapshots_xctx_strict` | 46,331 | 650 | 236 | 0 | 0 |
| `opening_gap_snapshots` | 9,438 | 41 | 396 | 0 | 0 |
| `opening_gap_snapshots_xctx` | 9,438 | 849 | 396 | 0 | 0 |
| `opening_gap_snapshots_xctx_gapctx` | 9,438 | 1,047 | 396 | 0 | 0 |
| `opening_gap_snapshots_xctx_gapctx_obgeom` | 9,438 | 1,708 | 396 | 0 | 0 |
| `opening_gap_snapshots_xctx_gapctx_obgeom_liqgeom` | 9,438 | 2,717 | 396 | 0 | 0 |
| `opening_gap_snapshots_xctx_gapctx_obgeom_liqgeom_regime` | 9,438 | 2,873 | 396 | 0 | 0 |
| `opening_gap_snapshots_xctx_gapctx_obgeom_liqgeom_regime_strict` | 9,438 | 2,873 | 423 | 0 | 0 |
| `orb_snapshots` | 34,040 | 40 | 38 | 0 | 0 |
| `psp_snapshots` | 15,827 | 51 | 33 | 0 | 0 |
| `smt_previous_day_snapshots` | 4,676 | 281 | 18 | 0 | 0 |
| `smt_previous_day_snapshots_xctx` | 4,676 | 873 | 18 | 0 | 0 |
| `smt_previous_day_snapshots_xctx_fvggeom` | 4,676 | 1,324 | 18 | 0 | 0 |
| `smt_previous_day_snapshots_xctx_fvggeom_obgeom` | 4,676 | 1,985 | 18 | 0 | 0 |
| `smt_previous_day_snapshots_xctx_fvggeom_obgeom_liqgeom` | 4,676 | 2,994 | 18 | 0 | 0 |
| `smt_previous_day_snapshots_xctx_fvggeom_obgeom_liqgeom_regime` | 4,676 | 3,150 | 18 | 0 | 0 |
| `smt_weekly_snapshots` | 1,060 | 281 | 18 | 0 | 0 |
| `sweep_snapshots` | 52,946 | 46 | 95 | 0 | 0 |
| `sweep_snapshots_xctx` | 52,946 | 854 | 95 | 0 | 0 |
| `sweep_snapshots_xctx_fvggeom` | 52,946 | 1,305 | 95 | 0 | 0 |
| `sweep_snapshots_xctx_fvggeom_obgeom` | 52,946 | 1,966 | 95 | 0 | 0 |
| `sweep_snapshots_xctx_fvggeom_obgeom_liqgeom` | 52,946 | 2,975 | 95 | 0 | 0 |
| `sweep_snapshots_xctx_fvggeom_obgeom_liqgeom_regime` | 52,946 | 3,131 | 95 | 0 | 0 |
| `sweep_snapshots_xctx_fvggeom_obgeom_liqgeom_regime_strict` | 52,946 | 3,131 | 105 | 0 | 0 |
| `swing_snapshots` | 76,786 | 37 | 29 | 0 | 0 |
| `swing_snapshots_strict` | 76,786 | 37 | 39 | 0 | 0 |
| `tp_snapshots` | 19,414 | 46 | 24 | 0 | 0 |
| `tp_snapshots_xctx` | 19,414 | 626 | 24 | 0 | 0 |
| `tp_snapshots_xctx_fvggeom` | 19,414 | 1,077 | 24 | 0 | 0 |
| `tp_snapshots_xctx_fvggeom_obgeom` | 19,414 | 1,738 | 24 | 0 | 0 |
| `vp_snapshots` | 36,095 | 65 | 139 | 0 | 0 |
| `vp_snapshots_xctx` | 36,095 | 657 | 139 | 0 | 0 |
| `vp_snapshots_xctx_obgeom` | 36,095 | 1,318 | 139 | 0 | 0 |

## Issues

_None._

## Expected Warnings

Phase 1 matrices store outcomes beside event-time fields. That is useful for research but unsafe unless model scripts exclude them.

| Severity | Dataset | Message | Examples |
|---|---|---|---|
| expected | `disp` | Phase 1 matrix contains outcome columns; exclude these from model features. | `oc.schema_version`, `oc.outcome_version`, `oc.thesis_direction`, `oc.reference_close`, `oc.displacement_levels.open` |
| expected | `eql` | Phase 1 matrix contains outcome columns; exclude these from model features. | `oc.schema_version`, `oc.outcome_version`, `oc.level_price`, `oc.side`, `oc.thesis_direction` |
| expected | `ft` | Phase 1 matrix contains outcome columns; exclude these from model features. | `oc.schema_version`, `oc.outcome_version`, `oc.reference_close`, `oc.first_third_direction`, `oc.parent_direction` |
| expected | `fvg` | Phase 1 matrix contains outcome columns; exclude these from model features. | `oc.schema_version`, `oc.outcome_version`, `oc.thesis_direction`, `oc.reference_close`, `oc.fvg_high` |
| expected | `fvp` | Phase 1 matrix contains outcome columns; exclude these from model features. | `oc.schema_version`, `oc.outcome_version`, `oc.reference_close`, `oc.forward_window_start_utc`, `oc.forward_window_end_utc` |
| expected | `itr` | Phase 1 matrix contains outcome columns; exclude these from model features. | `oc.schema_version`, `oc.outcome_version`, `oc.reference_close`, `oc.interval_high`, `oc.interval_low` |
| expected | `macro` | Phase 1 matrix contains outcome columns; exclude these from model features. | `oc.schema_version`, `oc.outcome_version`, `oc.release_ts_utc`, `oc.reference_close`, `oc.max_horizon_minutes` |
| expected | `ob` | Phase 1 matrix contains outcome columns; exclude these from model features. | `oc.schema_version`, `oc.outcome_version`, `oc.thesis_direction`, `oc.reference_close`, `oc.ob_levels.open` |
| expected | `ogap` | Phase 1 matrix contains outcome columns; exclude these from model features. | `oc.schema_version`, `oc.outcome_version`, `oc.reference_price`, `oc.max_horizon_minutes`, `oc.full_horizon.window_start_utc` |
| expected | `orb` | Phase 1 matrix contains outcome columns; exclude these from model features. | `oc.schema_version`, `oc.outcome_version`, `oc.reference_close`, `oc.or_direction`, `oc.rest_direction` |
| expected | `psp` | Phase 1 matrix contains outcome columns; exclude these from model features. | `oc.schema_version`, `oc.outcome_version`, `oc.minority_direction`, `oc.next_candle.ts_utc`, `oc.next_candle.open` |
| expected | `smt` | Phase 1 matrix contains outcome columns; exclude these from model features. | `oc.schema_version`, `oc.outcome_version`, `oc.thesis_direction`, `oc.period_close.ts_utc`, `oc.period_close.primary_close_price` |
| expected | `sweep` | Phase 1 matrix contains outcome columns; exclude these from model features. | `oc.schema_version`, `oc.outcome_version`, `oc.thesis_direction`, `oc.manipulation_close`, `oc.ref_price` |
| expected | `swing` | Phase 1 matrix contains outcome columns; exclude these from model features. | `oc.schema_version`, `oc.outcome_version`, `oc.thesis_direction`, `oc.pivot_price`, `oc.reference_close` |
| expected | `tp` | Phase 1 matrix contains outcome columns; exclude these from model features. | `oc.schema_version`, `oc.outcome_version`, `oc.thesis_direction`, `oc.reference_close`, `oc.parent_high` |
| expected | `vp` | Phase 1 matrix contains outcome columns; exclude these from model features. | `oc.schema_version`, `oc.outcome_version`, `oc.reference_close`, `oc.forward_window_start_utc`, `oc.forward_window_end_utc` |
