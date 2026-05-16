# ML Feature Dictionary

_Generated `2026-05-16T01:11:31.315128+00:00`._

This is the database map. It explains column families, which matrices use them, and which parts are features versus labels.

## Totals

- Phase 1 feature matrices: `16`
- Snapshot matrices: `53`
- Column families: `35`

## Column Families

| Prefix | Family | Datasets | Column refs | Meaning |
|---|---|---|---|---|
| `(root)` | raw_metadata | 19 | 162 | Top-level event identifiers, timestamp pieces, side, symbol, and event type. |
| `anchor.` | anchor_metadata | 52 | 351 | Anchor event identifiers and raw event-time metadata. |
| `asof.` | snapshot_metadata | 52 | 254 | Snapshot identity, cutoff timestamp, and label window timestamps. |
| `ctx.` | raw_context | 16 | 58 | Flattened detector context fields captured at event creation. |
| `disp.` | displacement_event_time | 1 | 29 | Filtered displacement-candle event-time fields knowable at detector fire. |
| `ed.` | raw_event_data | 16 | 500 | Flattened detector payload from the original event. Safe only when the event is already knowable. |
| `eql.` | equal_levels_event_time | 1 | 24 | Filtered equal-level fields knowable after the confirming pivot is knowable. |
| `ft.` | first_third_event_time | 1 | 25 | Filtered first-third range fields knowable after the first-third window closes. |
| `fvg.` | fvg_event_time | 5 | 150 | Filtered FVG event-time fields knowable at detector fire. |
| `fvggeom.` | fvg_geometry_context | 14 | 6,314 | State-aware nearest FVG zone geometry known by the snapshot cutoff. |
| `fvp.` | forming_volume_profile_event_time | 4 | 216 | Filtered forming volume-profile fields knowable at the as-of snapshot cutoff. |
| `gapctx.` | opening_gap_memory_context | 7 | 1,386 | State-aware nearest NDOG/NWOG memory levels known by the snapshot cutoff. |
| `itr.` | interval_true_range_event_time | 2 | 168 | Completed daily/weekly/session interval range fields known after the interval closes. |
| `label.` | forward_label | 50 | 8,271 | Forward prediction targets. These must never be fed back as model features. |
| `liqgeom.` | swing_equal_level_geometry_context | 8 | 8,072 | State-aware nearest swing/equal-high/equal-low liquidity levels known by the snapshot cutoff. |
| `macro.` | macro_event_time | 2 | 102 | Scheduled macro-event fields known before release plus pre-release market context. |
| `next_15m.` | unregistered | 1 | 36 | No explicit registry description yet; inspect the owning detector/schema. |
| `next_5m.` | unregistered | 1 | 3 | No explicit registry description yet; inspect the owning detector/schema. |
| `next_60m.` | unregistered | 1 | 9 | No explicit registry description yet; inspect the owning detector/schema. |
| `ob.` | order_block_event_time | 2 | 86 | Filtered order-block event-time fields knowable at detector fire. |
| `obgeom.` | order_block_geometry_context | 16 | 10,576 | State-aware nearest order-block zone geometry known by the snapshot cutoff. |
| `oc.` | raw_outcomes | 16 | 2,354 | Flattened forward outcomes. These are labels or diagnostics, not model features unless explicitly converted. |
| `ogap.` | opening_gap_event_time | 7 | 154 | Filtered NDOG/NWOG level fields knowable at the new day/week open. |
| `orb.` | opening_range_event_time | 1 | 25 | Filtered opening-range fields knowable after the range window closes. |
| `pc.` | period_close | 9 | 1,696 | Fields and aligned event flags knowable only by period N close. |
| `psp.` | psp_event_time | 1 | 36 | Filtered PSP event-time fields knowable at detector fire. |
| `regime.` | completed_interval_regime_context | 5 | 780 | Completed session/day/week true-range regime features known before the snapshot cutoff. |
| `smt.` | smt_event_time | 7 | 168 | Filtered SMT fields knowable at first divergent break. |
| `sweep.` | sweep_event_time | 7 | 189 | Filtered liquidity-sweep event-time fields knowable at detector fire. |
| `swing.` | swing_pivot_event_time | 2 | 44 | Filtered swing-pivot fields knowable after right-side confirmation bars. |
| `tp.` | time_profile_event_time | 4 | 124 | Filtered time-profile fields knowable after the parent period closes. |
| `ts.` | time | 50 | 200 | Calendar features computed from the snapshot timestamp. |
| `vp.` | volume_profile_event_time | 3 | 150 | Filtered volume-profile fields knowable after the parent period closes. |
| `xctx.` | cross_concept_context | 32 | 23,396 | Generated cross-concept prior-event counts, flags, and age features. |
| `xd.` | prior_cross_detector | 66 | 888 | Coarse Phase 1 flags for prior detector events before anchor fire. |

## Phase 1 Feature Matrices

| Concept | Rows | Cols | Prefix counts |
|---|---|---|---|
| `disp` | 38,747 | 91 | `(root)` 9, `ctx.` 3, `ed.` 20, `oc.` 45, `xd.` 14 |
| `eql` | 60,338 | 81 | `(root)` 9, `ctx.` 4, `ed.` 13, `oc.` 41, `xd.` 14 |
| `ft` | 10,373 | 97 | `(root)` 9, `ctx.` 2, `ed.` 20, `oc.` 52, `xd.` 14 |
| `fvg` | 209,339 | 169 | `(root)` 9, `ctx.` 3, `ed.` 23, `oc.` 119, `xd.` 15 |
| `fvp` | 43,150 | 592 | `(root)` 9, `ctx.` 3, `ed.` 47, `oc.` 518, `xd.` 15 |
| `itr` | 36,095 | 172 | `(root)` 9, `ctx.` 4, `ed.` 78, `oc.` 66, `xd.` 15 |
| `macro` | 18,414 | 468 | `(root)` 9, `ctx.` 5, `ed.` 50, `oc.` 389, `xd.` 15 |
| `ob` | 46,331 | 297 | `(root)` 9, `ctx.` 6, `ed.` 38, `oc.` 230, `xd.` 14 |
| `ogap` | 9,438 | 487 | `(root)` 9, `ctx.` 3, `ed.` 18, `oc.` 442, `xd.` 15 |
| `orb` | 34,040 | 99 | `(root)` 9, `ctx.` 2, `ed.` 21, `oc.` 53, `xd.` 14 |
| `psp` | 15,827 | 88 | `(root)` 9, `ctx.` 3, `ed.` 26, `oc.` 36, `xd.` 14 |
| `smt` | 2,891 | 121 | `(root)` 9, `ctx.` 5, `ed.` 44, `oc.` 49, `xd.` 14 |
| `sweep` | 52,946 | 155 | `(root)` 9, `ctx.` 6, `ed.` 20, `oc.` 105, `xd.` 15 |
| `swing` | 76,786 | 73 | `(root)` 9, `ctx.` 3, `ed.` 14, `oc.` 33, `xd.` 14 |
| `tp` | 19,414 | 84 | `(root)` 9, `ctx.` 3, `ed.` 26, `oc.` 32, `xd.` 14 |
| `vp` | 36,095 | 212 | `(root)` 9, `ctx.` 3, `ed.` 42, `oc.` 144, `xd.` 14 |

## Snapshot Matrices

| Matrix | Concept | Rows | Cols | Feature cols | Label cols |
|---|---|---|---|---|---|
| `disp_snapshots` | `disp` | 38,747 | 89 | 44 | 33 |
| `eql_snapshots` | `eql` | 60,338 | 89 | 39 | 38 |
| `ft_snapshots` | `ft` | 10,373 | 89 | 40 | 37 |
| `fvg_snapshots` | `fvg` | 209,339 | 170 | 49 | 109 |
| `fvg_snapshots_xctx` | `fvg` | 209,339 | 978 | 857 | 109 |
| `fvg_snapshots_xctx_fvggeom` | `fvg` | 209,339 | 1,429 | 1,308 | 109 |
| `fvg_snapshots_xctx_fvggeom_obgeom` | `fvg` | 209,339 | 2,090 | 1,969 | 109 |
| `fvg_snapshots_xctx_fvggeom_obgeom_strict` | `fvg` | 209,339 | 2,114 | 1,969 | 133 |
| `forming_vp_snapshots` | `fvp` | 43,150 | 592 | 73 | 507 |
| `forming_vp_snapshots_xctx` | `fvp` | 43,150 | 1,388 | 869 | 507 |
| `forming_vp_snapshots_xctx_gapctx` | `fvp` | 43,150 | 1,586 | 1,067 | 507 |
| `forming_vp_snapshots_xctx_gapctx_obgeom` | `fvp` | 43,150 | 2,247 | 1,728 | 507 |
| `itr_snapshots` | `itr` | 36,095 | 174 | 103 | 59 |
| `itr_snapshots_xctx` | `itr` | 36,095 | 970 | 899 | 59 |
| `macro_event_snapshots` | `macro` | 18,414 | 454 | 70 | 372 |
| `macro_event_snapshots_xctx` | `macro` | 18,414 | 1,262 | 878 | 372 |
| `macro_event_type_breakdown` | `macro` | 70 | 56 | 0 | 0 |
| `ob_snapshots` | `ob` | 46,331 | 296 | 58 | 226 |
| `ob_snapshots_xctx` | `ob` | 46,331 | 888 | 650 | 226 |
| `opening_gap_snapshots` | `ogap` | 9,438 | 449 | 41 | 396 |
| `opening_gap_snapshots_xctx` | `ogap` | 9,438 | 1,257 | 849 | 396 |
| `opening_gap_snapshots_xctx_gapctx` | `ogap` | 9,438 | 1,455 | 1,047 | 396 |
| `opening_gap_snapshots_xctx_gapctx_obgeom` | `ogap` | 9,438 | 2,116 | 1,708 | 396 |
| `opening_gap_snapshots_xctx_gapctx_obgeom_liqgeom` | `ogap` | 9,438 | 3,125 | 2,717 | 396 |
| `opening_gap_snapshots_xctx_gapctx_obgeom_liqgeom_regime` | `ogap` | 9,438 | 3,281 | 2,873 | 396 |
| `opening_gap_snapshots_xctx_gapctx_obgeom_liqgeom_regime_strict` | `ogap` | 9,438 | 3,308 | 2,873 | 423 |
| `orb_snapshots` | `orb` | 34,040 | 90 | 40 | 38 |
| `psp_snapshots` | `psp` | 15,827 | 96 | 51 | 33 |
| `smt_previous_day_snapshots` | `smt` | 4,676 | 310 | 281 | 18 |
| `smt_previous_day_snapshots_xctx` | `smt` | 4,676 | 902 | 873 | 18 |
| `smt_previous_day_snapshots_xctx_fvggeom` | `smt` | 4,676 | 1,353 | 1,324 | 18 |
| `smt_previous_day_snapshots_xctx_fvggeom_obgeom` | `smt` | 4,676 | 2,014 | 1,985 | 18 |
| `smt_previous_day_snapshots_xctx_fvggeom_obgeom_liqgeom` | `smt` | 4,676 | 3,023 | 2,994 | 18 |
| `smt_previous_day_snapshots_xctx_fvggeom_obgeom_liqgeom_regime` | `smt` | 4,676 | 3,179 | 3,150 | 18 |
| `smt_snapshot_model_predictions` | `smt` | 1,137 | 12 | 0 | 0 |
| `smt_snapshot_model_predictions_at_fire_low` | `smt` | 1,137 | 12 | 0 | 0 |
| `smt_weekly_snapshots` | `smt` | 1,060 | 310 | 281 | 18 |
| `sweep_snapshots` | `sweep` | 52,946 | 153 | 46 | 95 |
| `sweep_snapshots_xctx` | `sweep` | 52,946 | 961 | 854 | 95 |
| `sweep_snapshots_xctx_fvggeom` | `sweep` | 52,946 | 1,412 | 1,305 | 95 |
| `sweep_snapshots_xctx_fvggeom_obgeom` | `sweep` | 52,946 | 2,073 | 1,966 | 95 |
| `sweep_snapshots_xctx_fvggeom_obgeom_liqgeom` | `sweep` | 52,946 | 3,082 | 2,975 | 95 |
| `sweep_snapshots_xctx_fvggeom_obgeom_liqgeom_regime` | `sweep` | 52,946 | 3,238 | 3,131 | 95 |
| `sweep_snapshots_xctx_fvggeom_obgeom_liqgeom_regime_strict` | `sweep` | 52,946 | 3,248 | 3,131 | 105 |
| `swing_snapshots` | `swing` | 76,786 | 78 | 37 | 29 |
| `swing_snapshots_strict` | `swing` | 76,786 | 88 | 37 | 39 |
| `tp_snapshots` | `tp` | 19,414 | 82 | 46 | 24 |
| `tp_snapshots_xctx` | `tp` | 19,414 | 662 | 626 | 24 |
| `tp_snapshots_xctx_fvggeom` | `tp` | 19,414 | 1,113 | 1,077 | 24 |
| `tp_snapshots_xctx_fvggeom_obgeom` | `tp` | 19,414 | 1,774 | 1,738 | 24 |
| `vp_snapshots` | `vp` | 36,095 | 216 | 65 | 139 |
| `vp_snapshots_xctx` | `vp` | 36,095 | 808 | 657 | 139 |
| `vp_snapshots_xctx_obgeom` | `vp` | 36,095 | 1,469 | 1,318 | 139 |

## How To Read Columns

- `anchor.*` and `asof.*` identify the anchor event and the exact cutoff used for features.
- `<concept>.ed.*` means detector event data for the anchor concept, filtered into a snapshot namespace.
- `xctx.*` means prior cross-concept counts/ages known before the cutoff.
- `fvggeom.*`, `obgeom.*`, and `gapctx.*` mean state-aware level geometry built from prior events only.
- `label.*` is a target. It is not a feature.

## Machine-Readable Copy

- JSON: `C:\Users\benbr\BacktestStation\data\ml\catalog\feature_dictionary.json`
