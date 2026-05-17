# ML Feature Dictionary

_Generated `2026-05-17T22:15:40.580612+00:00`._

This is the database map. It explains column families, which matrices use them, and which parts are features versus labels.

## Totals

- Phase 1 feature matrices: `17`
- Snapshot matrices: `59`
- Column families: `39`

## Column Families

| Prefix | Family | Datasets | Column refs | Meaning |
|---|---|---|---|---|
| `(root)` | raw_metadata | 23 | 204 | Top-level event identifiers, timestamp pieces, side, symbol, and event type. |
| `anchor.` | anchor_metadata | 55 | 370 | Anchor event identifiers and raw event-time metadata. |
| `asof.` | snapshot_metadata | 55 | 269 | Snapshot identity, cutoff timestamp, and label window timestamps. |
| `ctx.` | raw_context | 18 | 68 | Flattened detector context fields captured at event creation. |
| `data_level.` | unregistered | 1 | 58 | No explicit registry description yet; inspect the owning detector/schema. |
| `disp.` | displacement_event_time | 1 | 29 | Filtered displacement-candle event-time fields knowable at detector fire. |
| `ed.` | raw_event_data | 18 | 792 | Flattened detector payload from the original event. Safe only when the event is already knowable. |
| `eql.` | equal_levels_event_time | 1 | 24 | Filtered equal-level fields knowable after the confirming pivot is knowable. |
| `ft.` | first_third_event_time | 1 | 21 | Filtered first-third range fields knowable after the first-third window closes. |
| `fvg.` | fvg_event_time | 5 | 138 | Filtered FVG event-time fields knowable at detector fire. |
| `fvggeom.` | fvg_geometry_context | 15 | 6,765 | State-aware nearest FVG zone geometry known by the snapshot cutoff. |
| `fvp.` | forming_volume_profile_event_time | 4 | 198 | Filtered forming volume-profile fields knowable at the as-of snapshot cutoff. |
| `gapctx.` | opening_gap_memory_context | 7 | 1,386 | State-aware nearest NDOG/NWOG memory levels known by the snapshot cutoff. |
| `itr.` | interval_true_range_event_time | 2 | 154 | Completed daily/weekly/session interval range fields known after the interval closes. |
| `label.` | forward_label | 53 | 7,055 | Forward prediction targets. These must never be fed back as model features. |
| `liqgeom.` | swing_equal_level_geometry_context | 8 | 8,072 | State-aware nearest swing/equal-high/equal-low liquidity levels known by the snapshot cutoff. |
| `macro.` | macro_event_time | 2 | 102 | Scheduled macro-event fields known before release plus pre-release market context. |
| `news.` | unregistered | 2 | 9 | No explicit registry description yet; inspect the owning detector/schema. |
| `next_15m.` | unregistered | 1 | 36 | No explicit registry description yet; inspect the owning detector/schema. |
| `next_5m.` | unregistered | 1 | 3 | No explicit registry description yet; inspect the owning detector/schema. |
| `next_60m.` | unregistered | 1 | 9 | No explicit registry description yet; inspect the owning detector/schema. |
| `ob.` | order_block_event_time | 3 | 121 | Filtered order-block event-time fields knowable at detector fire. |
| `obgeom.` | order_block_geometry_context | 16 | 10,576 | State-aware nearest order-block zone geometry known by the snapshot cutoff. |
| `oc.` | raw_outcomes | 18 | 2,326 | Flattened forward outcomes. These are labels or diagnostics, not model features unless explicitly converted. |
| `ogap.` | opening_gap_event_time | 7 | 136 | Filtered NDOG/NWOG level fields knowable at the new day/week open. |
| `orb.` | opening_range_event_time | 1 | 22 | Filtered opening-range fields knowable after the range window closes. |
| `pc.` | period_close | 11 | 2,180 | Fields and aligned event flags knowable only by period N close. |
| `postx.` | unregistered | 1 | 45 | No explicit registry description yet; inspect the owning detector/schema. |
| `prex.` | unregistered | 1 | 27 | No explicit registry description yet; inspect the owning detector/schema. |
| `psp.` | psp_event_time | 1 | 36 | Filtered PSP event-time fields knowable at detector fire. |
| `regime.` | completed_interval_regime_context | 5 | 780 | Completed session/day/week true-range regime features known before the snapshot cutoff. |
| `smt.` | smt_event_time | 9 | 396 | Filtered SMT fields knowable at first divergent break. |
| `sweep.` | sweep_event_time | 7 | 156 | Filtered liquidity-sweep event-time fields knowable at detector fire. |
| `swing.` | swing_pivot_event_time | 2 | 40 | Filtered swing-pivot fields knowable after right-side confirmation bars. |
| `tp.` | time_profile_event_time | 4 | 100 | Filtered time-profile fields knowable after the parent period closes. |
| `ts.` | time | 53 | 212 | Calendar features computed from the snapshot timestamp. |
| `vp.` | volume_profile_event_time | 3 | 138 | Filtered volume-profile fields knowable after the parent period closes. |
| `xctx.` | cross_concept_context | 35 | 25,136 | Generated cross-concept prior-event counts, flags, and age features. |
| `xd.` | prior_cross_detector | 71 | 993 | Coarse Phase 1 flags for prior detector events before anchor fire. |

## Phase 1 Feature Matrices

| Concept | Rows | Cols | Prefix counts |
|---|---|---|---|
| `disp` | 214,599 | 93 | `(root)` 9, `ctx.` 3, `ed.` 20, `oc.` 45, `xd.` 16 |
| `eql` | 61,185 | 83 | `(root)` 9, `ctx.` 5, `ed.` 13, `oc.` 41, `xd.` 15 |
| `ft` | 52,791 | 97 | `(root)` 9, `ctx.` 2, `ed.` 20, `oc.` 52, `xd.` 14 |
| `fvg` | 1,243,757 | 124 | `(root)` 9, `ctx.` 3, `ed.` 23, `oc.` 75, `xd.` 14 |
| `fvp` | 1,132,868 | 495 | `(root)` 9, `ctx.` 3, `ed.` 47, `oc.` 422, `xd.` 14 |
| `itr` | 190,192 | 143 | `(root)` 9, `ctx.` 4, `ed.` 78, `oc.` 38, `xd.` 14 |
| `macro` | 18,414 | 468 | `(root)` 9, `ctx.` 5, `ed.` 50, `oc.` 389, `xd.` 15 |
| `ob` | 198,069 | 297 | `(root)` 9, `ctx.` 6, `ed.` 38, `oc.` 230, `xd.` 14 |
| `ogap` | 36,944 | 210 | `(root)` 9, `ctx.` 3, `ed.` 18, `oc.` 166, `xd.` 14 |
| `orb` | 158,941 | 99 | `(root)` 9, `ctx.` 2, `ed.` 21, `oc.` 53, `xd.` 14 |
| `psp` | 77,933 | 90 | `(root)` 9, `ctx.` 3, `ed.` 26, `oc.` 36, `xd.` 16 |
| `smt` | 10,889 | 301 | `(root)` 9, `ctx.` 5, `ed.` 224, `oc.` 49, `xd.` 14 |
| `smt_mtf` | 244,615 | 190 | `(root)` 9, `ctx.` 4, `ed.` 62, `oc.` 99, `xd.` 16 |
| `sweep` | 237,569 | 82 | `(root)` 9, `ctx.` 6, `ed.` 20, `oc.` 33, `xd.` 14 |
| `swing` | 345,702 | 73 | `(root)` 9, `ctx.` 3, `ed.` 14, `oc.` 33, `xd.` 14 |
| `tp` | 105,819 | 84 | `(root)` 9, `ctx.` 3, `ed.` 26, `oc.` 32, `xd.` 14 |
| `vp` | 183,662 | 212 | `(root)` 9, `ctx.` 3, `ed.` 42, `oc.` 144, `xd.` 14 |

## Snapshot Matrices

| Matrix | Concept | Rows | Cols | Feature cols | Label cols |
|---|---|---|---|---|---|
| `disp_snapshots` | `disp` | 214,599 | 94 | 49 | 33 |
| `eql_snapshots` | `eql` | 60,338 | 89 | 39 | 38 |
| `ft_snapshots` | `ft` | 52,791 | 88 | 39 | 37 |
| `fvg_snapshots` | `fvg` | 1,243,757 | 123 | 44 | 67 |
| `fvg_snapshots_xctx` | `fvg` | 1,243,757 | 835 | 756 | 67 |
| `fvg_snapshots_xctx_fvggeom` | `fvg` | 1,243,757 | 1,286 | 1,207 | 67 |
| `fvg_snapshots_xctx_fvggeom_obgeom` | `fvg` | 209,339 | 2,090 | 1,969 | 109 |
| `fvg_snapshots_xctx_fvggeom_obgeom_strict` | `fvg` | 209,339 | 2,114 | 1,969 | 133 |
| `forming_vp_snapshots` | `fvp` | 1,132,868 | 489 | 66 | 411 |
| `forming_vp_snapshots_xctx` | `fvp` | 1,132,868 | 1,189 | 766 | 411 |
| `forming_vp_snapshots_xctx_gapctx` | `fvp` | 1,132,868 | 1,387 | 964 | 411 |
| `forming_vp_snapshots_xctx_gapctx_obgeom` | `fvp` | 43,150 | 2,247 | 1,728 | 507 |
| `itr_snapshots` | `itr` | 190,192 | 142 | 95 | 35 |
| `itr_snapshots_xctx` | `itr` | 190,192 | 842 | 795 | 35 |
| `macro_event_snapshots` | `macro` | 18,414 | 454 | 70 | 372 |
| `macro_event_snapshots_xctx` | `macro` | 18,414 | 1,262 | 878 | 372 |
| `macro_event_type_breakdown` | `macro` | 70 | 56 | 0 | 0 |
| `macro_news_interaction_summary` | `macro` | 260 | 8 | 0 | 0 |
| `macro_news_interactions` | `macro` | 18,414 | 606 | 0 | 0 |
| `macro_news_level_reaction_stats` | `macro` | 785 | 17 | 0 | 0 |
| `ob_snapshots` | `ob` | 198,069 | 291 | 53 | 226 |
| `ob_snapshots_xctx` | `ob` | 46,331 | 888 | 650 | 226 |
| `ob_snapshots_xctx_strict` | `ob` | 46,331 | 898 | 650 | 236 |
| `opening_gap_snapshots` | `ogap` | 36,944 | 168 | 34 | 122 |
| `opening_gap_snapshots_xctx` | `ogap` | 36,944 | 880 | 746 | 122 |
| `opening_gap_snapshots_xctx_gapctx` | `ogap` | 36,944 | 1,078 | 944 | 122 |
| `opening_gap_snapshots_xctx_gapctx_obgeom` | `ogap` | 9,438 | 2,116 | 1,708 | 396 |
| `opening_gap_snapshots_xctx_gapctx_obgeom_liqgeom` | `ogap` | 9,438 | 3,125 | 2,717 | 396 |
| `opening_gap_snapshots_xctx_gapctx_obgeom_liqgeom_regime` | `ogap` | 9,438 | 3,281 | 2,873 | 396 |
| `opening_gap_snapshots_xctx_gapctx_obgeom_liqgeom_regime_strict` | `ogap` | 9,438 | 3,308 | 2,873 | 423 |
| `orb_snapshots` | `orb` | 158,941 | 90 | 40 | 38 |
| `psp_snapshots` | `psp` | 77,933 | 101 | 56 | 33 |
| `smt_previous_day_snapshots` | `smt` | 15,690 | 343 | 314 | 18 |
| `smt_previous_day_snapshots_xctx` | `smt` | 15,690 | 1,055 | 1,026 | 18 |
| `smt_previous_day_snapshots_xctx_fvggeom` | `smt` | 15,690 | 1,506 | 1,477 | 18 |
| `smt_previous_day_snapshots_xctx_fvggeom_obgeom` | `smt` | 4,676 | 2,014 | 1,985 | 18 |
| `smt_previous_day_snapshots_xctx_fvggeom_obgeom_liqgeom` | `smt` | 4,676 | 3,023 | 2,994 | 18 |
| `smt_previous_day_snapshots_xctx_fvggeom_obgeom_liqgeom_regime` | `smt` | 4,676 | 3,179 | 3,150 | 18 |
| `smt_snapshot_model_predictions` | `smt` | 1,137 | 12 | 0 | 0 |
| `smt_snapshot_model_predictions_at_fire_low` | `smt` | 1,137 | 12 | 0 | 0 |
| `smt_weekly_snapshots` | `smt` | 5,964 | 343 | 314 | 18 |
| `smt_weekly_snapshots_xctx` | `smt` | 5,964 | 1,055 | 1,026 | 18 |
| `smt_weekly_snapshots_xctx_fvggeom` | `smt` | 5,964 | 1,506 | 1,477 | 18 |
| `sweep_snapshots` | `sweep` | 237,569 | 73 | 34 | 27 |
| `sweep_snapshots_xctx` | `sweep` | 237,569 | 785 | 746 | 27 |
| `sweep_snapshots_xctx_fvggeom` | `sweep` | 237,569 | 1,236 | 1,197 | 27 |
| `sweep_snapshots_xctx_fvggeom_obgeom` | `sweep` | 52,946 | 2,073 | 1,966 | 95 |
| `sweep_snapshots_xctx_fvggeom_obgeom_liqgeom` | `sweep` | 52,946 | 3,082 | 2,975 | 95 |
| `sweep_snapshots_xctx_fvggeom_obgeom_liqgeom_regime` | `sweep` | 52,946 | 3,238 | 3,131 | 95 |
| `sweep_snapshots_xctx_fvggeom_obgeom_liqgeom_regime_strict` | `sweep` | 52,946 | 3,248 | 3,131 | 105 |
| `swing_snapshots` | `swing` | 345,702 | 77 | 36 | 29 |
| `swing_snapshots_strict` | `swing` | 76,786 | 88 | 37 | 39 |
| `tp_snapshots` | `tp` | 105,819 | 77 | 41 | 24 |
| `tp_snapshots_xctx` | `tp` | 105,819 | 777 | 741 | 24 |
| `tp_snapshots_xctx_fvggeom` | `tp` | 105,819 | 1,228 | 1,192 | 24 |
| `tp_snapshots_xctx_fvggeom_obgeom` | `tp` | 19,414 | 1,774 | 1,738 | 24 |
| `vp_snapshots` | `vp` | 183,662 | 213 | 62 | 139 |
| `vp_snapshots_xctx` | `vp` | 183,662 | 913 | 762 | 139 |
| `vp_snapshots_xctx_obgeom` | `vp` | 36,095 | 1,469 | 1,318 | 139 |

## How To Read Columns

- `anchor.*` and `asof.*` identify the anchor event and the exact cutoff used for features.
- `<concept>.ed.*` means detector event data for the anchor concept, filtered into a snapshot namespace.
- `xctx.*` means prior cross-concept counts/ages known before the cutoff.
- `fvggeom.*`, `obgeom.*`, and `gapctx.*` mean state-aware level geometry built from prior events only.
- `label.*` is a target. It is not a feature.

## Machine-Readable Copy

- JSON: `C:\Users\benbr\BacktestStation\data\ml\catalog\feature_dictionary.json`
