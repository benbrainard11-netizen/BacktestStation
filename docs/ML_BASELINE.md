# ML baseline screening — per detector × label

_Generated `2026-05-10T23:41:30.175928+00:00`._

Chronological split: train ≤ 2022 / val = 2023 / test ≥ 2024.

Each row trains logistic regression + LightGBM on the given (detector, label) pair. **lift_vs_majority** = lgb_test_acc − majority_test_acc. Sorted by lgb_test_auc desc.

Skipped reasons:
- `missing_label`: label column not in feature matrix
- `skip_non_bool`: label is multi-class (handled later)
- `too_few_labels`: < 200 events with non-null label
- `small_split`: < 100 train OR < 50 test events
- `class_imbalance` / `test_imbalance`: < 50 / < 20 of either class

Leakage control: detector-specific `event_data` exclusions are applied before training. For SMT this drops post-fire confirmation fields (`did_all_confirm_by_window_end`, `later_confirmations`, `divergence_duration_seconds`, and lagger break flags/prices/times) while preserving prior-period reference levels. See `docs/ML_BASELINE_LEAKAGE_AUDIT.md`.

| detector | label | n_train | n_test | majority_test_acc | lr_test_acc | lr_test_auc | lgb_test_acc | lgb_test_auc | lgb_lift_vs_majority | status |
|---|---|---|---|---|---|---|---|---|---|---|
| ob | oc.level_tags.open.wick_tapped | 33438 | 8764 | 0.953 | 0.953 | 0.882 | 0.951 | 0.87 | -0.002 | ok |
| sweep | oc.ob_confirmation.did_confirm | 37982 | 10146 | 0.958 | 0.958 | 0.845 | 0.96 | 0.865 | 0.002 | ok |
| smt | oc.period_close.smt_active_for_side_at_close | 1935 | 644 | 0.671 | 0.8 | 0.81 | 0.818 | 0.819 | 0.147 | ok |
| vp | oc.took_period_high | 24728 | 6543 | 0.683 | 0.761 | 0.801 | 0.763 | 0.802 | 0.08 | ok |
| sweep | oc.swept_level_recovery.level_recovered | 37982 | 10146 | 0.705 | 0.751 | 0.774 | 0.765 | 0.796 | 0.06 | ok |
| vp | oc.took_period_low | 24728 | 6543 | 0.601 | 0.727 | 0.784 | 0.732 | 0.786 | 0.131 | ok |
| fvg | oc.mitigation.fully_filled | 148635 | 41532 | 0.777 | 0.789 | 0.741 | 0.805 | 0.77 | 0.028 | ok |
| tp | oc.next_period.took_parent_high | 13808 | 3666 | 0.562 | 0.688 | 0.749 | 0.707 | 0.768 | 0.145 | ok |
| fvg | oc.mitigation.closed_through | 148635 | 41532 | 0.688 | 0.729 | 0.719 | 0.742 | 0.748 | 0.054 | ok |
| tp | oc.next_period.took_parent_low | 13808 | 3666 | 0.565 | 0.672 | 0.722 | 0.676 | 0.741 | 0.111 | ok |
| ob | oc.level_tags.close.wick_tapped | 33438 | 8764 | 0.892 | 0.892 | 0.742 | 0.893 | 0.731 | 0.001 | ok |
| fvg | oc.mitigation.tapped | 148635 | 41532 | 0.866 | 0.865 | 0.703 | 0.867 | 0.729 | 0.001 | ok |
| ft | oc.break_high.wick_breached | 7448 | 1986 | 0.812 | 0.81 | 0.726 | 0.812 | 0.715 | 0.0 | ok |
| fvg | oc.mitigation.closed_inside | 148635 | 41532 | 0.559 | 0.616 | 0.645 | 0.658 | 0.708 | 0.099 | ok |
| orb | oc.break_high.wick_breached | 24460 | 6510 | 0.785 | 0.785 | 0.703 | 0.783 | 0.7 | -0.002 | ok |
| orb | oc.break_low.wick_breached | 24460 | 6510 | 0.767 | 0.771 | 0.695 | 0.771 | 0.695 | 0.004 | ok |
| ft | oc.break_low.wick_breached | 7448 | 1986 | 0.742 | 0.758 | 0.7 | 0.75 | 0.689 | 0.008 | ok |
| disp | oc.retracement.tapped_open | 27706 | 7430 | 0.734 | 0.745 | 0.664 | 0.744 | 0.672 | 0.01 | ok |
| swing | oc.breakout.wick_taken | 55047 | 14738 | 0.698 | 0.704 | 0.64 | 0.721 | 0.671 | 0.023 | ok |
| ob | oc.invalidation.invalidated | 33438 | 8764 | 0.808 | 0.808 | 0.684 | 0.811 | 0.664 | 0.003 | ok |
| tp | oc.next_period.thesis_confirmed | 13808 | 3666 | 0.672 | 0.675 | 0.663 | 0.679 | 0.662 | 0.007 | ok |
| disp | oc.retracement.tapped_full | 27706 | 7430 | 0.693 | 0.705 | 0.649 | 0.703 | 0.658 | 0.01 | ok |
| disp | oc.invalidation.invalidated | 27706 | 7430 | 0.649 | 0.669 | 0.647 | 0.667 | 0.648 | 0.018 | ok |
| swing | oc.breakout.close_taken | 55047 | 14738 | 0.618 | 0.643 | 0.63 | 0.654 | 0.638 | 0.036 | ok |
| orb | oc.broke_both_sides | 24460 | 6510 | 0.556 | 0.607 | 0.628 | 0.615 | 0.631 | 0.059 | ok |
| sweep | oc.forward_continuation.continued | 37982 | 10146 | 0.911 | 0.912 | 0.667 | 0.911 | 0.629 | 0.0 | ok |
| eql | oc.take.wick_taken | 47141 | 8383 | 0.822 | 0.826 | 0.654 | 0.826 | 0.618 | 0.004 | ok |
| eql | oc.take.close_past | 47141 | 8383 | 0.771 | 0.775 | 0.642 | 0.774 | 0.567 | 0.003 | ok |
| smt | oc.next_period.primary_took_period_n_high | 1921 | 635 | 0.539 | 0.554 | 0.562 | 0.542 | 0.547 | 0.003 | ok |
| smt | oc.next_period.thesis_confirmed_strict | 1921 | 635 | 0.537 | 0.537 | 0.574 | 0.535 | 0.533 | -0.002 | ok |
| eql | oc.take.first_take_was_reversal | 37240 | 6891 | 0.504 | 0.503 | 0.508 | 0.506 | 0.529 | 0.002 | ok |
| smt | oc.n_plus_2.thesis_confirmed_strict | 1911 | 630 | 0.543 | 0.562 | 0.579 | 0.471 | 0.513 | -0.072 | ok |
| smt | oc.next_period.primary_took_period_n_low | 1921 | 635 | 0.553 | 0.57 | 0.581 | 0.551 | 0.507 | -0.002 | ok |
| ft | oc.rest_confirms_first_third | 7448 | 1986 | 0.513 | 0.541 | 0.549 | 0.513 | 0.484 | 0.0 | ok |
| ft | oc.rest_reverses_first_third | 7448 | 1986 | 0.494 | 0.535 | 0.549 | 0.487 | 0.473 | -0.007 | ok |
| psp | oc.next_candle.relative_to_minority | — | — | — | — | — | — | — | — | skip_non_bool |
| vp | oc.forward_close_in_value_area | — | — | — | — | — | — | — | — | class_imbalance |

## Top-10 features per OK label

### ob / `oc.level_tags.open.wick_tapped`

_test_auc=0.87, test_acc=0.951 vs majority 0.953_

| feature | gain |
|---|---|
| ed.confirms_close_gt_ob_high | 14345 |
| ed.confirms_close_gt_ob_open | 10319 |
| ed.ob_range_width_pts | 2706 |
| month | 2293 |
| ed.ob_body_width_pts | 2187 |
| hour_of_day_utc | 1911 |
| year | 1694 |
| ctx.day_of_week_et | 1451 |
| ctx.hour_of_day_et | 1343 |
| ed.bars_back_to_ob | 1276 |

### sweep / `oc.ob_confirmation.did_confirm`

_test_auc=0.865, test_acc=0.96 vs majority 0.958_

| feature | gain |
|---|---|
| day_of_week | 6824 |
| ctx.day_of_week_et | 6695 |
| ed.tracking_timeframe_1h | 2778 |
| ed.sweep_depth_pts | 2638 |
| month | 2343 |
| hour_of_day_utc | 1981 |
| event_type_pwh_4h | 1876 |
| year | 1866 |
| ctx.hour_of_day_et | 1461 |
| event_type_pdh_1h | 1401 |

### smt / `oc.period_close.smt_active_for_side_at_close`

_test_auc=0.819, test_acc=0.818 vs majority 0.671_

| feature | gain |
|---|---|
| hour_of_day_utc | 4274 |
| ctx.hour_of_day_et | 1305 |
| ed.first_break_price | 519 |
| event_type_previous_day_smt | 323 |
| ed.symbol_states.YM.c.0.reference_high | 304 |
| ed.lagging_symbols_at_break__len | 278 |
| ed.symbol_states.NQ.c.0.reference_high | 262 |
| month | 222 |
| ed.symbol_states.YM.c.0.reference_low | 208 |
| ed.symbol_states.ES.c.0.reference_high | 206 |

### vp / `oc.took_period_high`

_test_auc=0.802, test_acc=0.763 vs majority 0.683_

| feature | gain |
|---|---|
| ed.close_vs_vwap_sd | 20956 |
| ed.close_vs_vwap_pts | 15077 |
| ed.poc_volume | 6750 |
| ed.total_volume | 3634 |
| ed.poc_pct_in_range | 3084 |
| year | 1929 |
| ed.vwap_sd | 1882 |
| ed.close_vs_poc_pts | 1808 |
| event_type_asia_volume_profile | 1663 |
| ed.value_area_range_pts | 1662 |

### sweep / `oc.swept_level_recovery.level_recovered`

_test_auc=0.796, test_acc=0.765 vs majority 0.705_

| feature | gain |
|---|---|
| ed.sweep_depth_pts | 38283 |
| ed.swept_reference.level_price | 7113 |
| ed.manipulation_candle.high | 6387 |
| ed.tracking_timeframe_1h | 5751 |
| year | 4690 |
| ed.manipulation_candle.open | 3510 |
| side_high | 3380 |
| ed.manipulation_candle.low | 2882 |
| month | 2444 |
| hour_of_day_utc | 2252 |

### vp / `oc.took_period_low`

_test_auc=0.786, test_acc=0.732 vs majority 0.601_

| feature | gain |
|---|---|
| ed.close_vs_vwap_pts | 25153 |
| ed.close_vs_vwap_sd | 11845 |
| ed.poc_volume | 7756 |
| ed.total_volume | 3770 |
| ed.n_bars | 3229 |
| ed.poc_pct_in_range | 2587 |
| year | 1894 |
| ed.vwap_sd | 1352 |
| ed.close_vs_poc_pts | 1263 |
| month | 1064 |

### fvg / `oc.mitigation.fully_filled`

_test_auc=0.77, test_acc=0.805 vs majority 0.777_

| feature | gain |
|---|---|
| hour_of_day_utc | 86550 |
| ed.fvg_width_pts | 40004 |
| ctx.hour_of_day_et | 39092 |
| event_type_15m_fvg | 20816 |
| day_of_week | 7106 |
| year | 5713 |
| month | 5132 |
| ed.tracking_timeframe_15m | 4857 |
| side_bearish | 3037 |
| ed.candle_1.high | 2856 |

### tp / `oc.next_period.took_parent_high`

_test_auc=0.768, test_acc=0.707 vs majority 0.562_

| feature | gain |
|---|---|
| ed.is_bearish_classic_po3 | 13231 |
| ed.parent_body_pts | 6731 |
| ed.parent_direction_bearish | 2909 |
| ed.parent_range_pts | 2683 |
| side_bearish | 2348 |
| ed.parent_open | 1624 |
| ed.parent_high | 1263 |
| ed.parent_close | 964 |
| year | 944 |
| month | 930 |

### fvg / `oc.mitigation.closed_through`

_test_auc=0.748, test_acc=0.742 vs majority 0.688_

| feature | gain |
|---|---|
| hour_of_day_utc | 95951 |
| ctx.hour_of_day_et | 43068 |
| ed.fvg_width_pts | 27251 |
| event_type_15m_fvg | 16975 |
| day_of_week | 7558 |
| year | 5763 |
| side_bearish | 5716 |
| month | 4759 |
| ed.tracking_timeframe_15m | 3825 |
| ctx.day_of_week_et | 2876 |

### tp / `oc.next_period.took_parent_low`

_test_auc=0.741, test_acc=0.676 vs majority 0.565_

| feature | gain |
|---|---|
| ed.parent_body_pts | 7266 |
| side_bullish | 5127 |
| side_bearish | 4141 |
| ed.parent_direction_bullish | 3660 |
| ed.parent_range_pts | 3263 |
| year | 1576 |
| ed.parent_direction_bearish | 1524 |
| month | 1220 |
| ed.parent_high | 1203 |
| ed.parent_open | 1066 |

### ob / `oc.level_tags.close.wick_tapped`

_test_auc=0.731, test_acc=0.893 vs majority 0.892_

| feature | gain |
|---|---|
| ed.confirms_close_gt_ob_high | 7278 |
| ed.ob_body_width_pts | 4690 |
| ed.ob_range_width_pts | 2507 |
| year | 2403 |
| ed.confirms_close_gt_ob_open | 2311 |
| ctx.day_of_week_et | 2296 |
| hour_of_day_utc | 2287 |
| ctx.hour_of_day_et | 2220 |
| month | 2189 |
| ed.swept_reference.prior_period_label_session_ny | 1427 |

### fvg / `oc.mitigation.tapped`

_test_auc=0.729, test_acc=0.867 vs majority 0.866_

| feature | gain |
|---|---|
| hour_of_day_utc | 49660 |
| ctx.hour_of_day_et | 23188 |
| event_type_15m_fvg | 11630 |
| day_of_week | 4507 |
| ed.fvg_width_pts | 4223 |
| month | 3381 |
| ed.tracking_timeframe_15m | 2730 |
| year | 2659 |
| side_bearish | 2300 |
| xd.has_disp_in_24h | 2264 |

### ft / `oc.break_high.wick_breached`

_test_auc=0.715, test_acc=0.812 vs majority 0.812_

| feature | gain |
|---|---|
| side_bearish | 2634 |
| ed.first_third_range_pts | 2119 |
| ed.n_1m_bars_in_first_third | 1057 |
| month | 665 |
| year | 546 |
| ed.first_third_high | 461 |
| day_of_week | 458 |
| ed.ext_above_high_1x_range | 338 |
| ed.first_third_open | 292 |
| ed.ext_below_low_1x_range | 277 |

### fvg / `oc.mitigation.closed_inside`

_test_auc=0.708, test_acc=0.658 vs majority 0.559_

| feature | gain |
|---|---|
| hour_of_day_utc | 43845 |
| ed.fvg_width_pts | 39188 |
| ctx.hour_of_day_et | 17772 |
| event_type_15m_fvg | 15470 |
| year | 12497 |
| ed.fvg_mid | 7971 |
| day_of_week | 5578 |
| ed.candle_2.high | 4983 |
| ed.tracking_timeframe_15m | 4274 |
| ed.candle_1.high | 3767 |

### orb / `oc.break_high.wick_breached`

_test_auc=0.7, test_acc=0.783 vs majority 0.785_

| feature | gain |
|---|---|
| side_bearish | 7882 |
| ed.or_range_pts | 3289 |
| side_bullish | 1902 |
| month | 1857 |
| ed.or_direction_bearish | 1464 |
| year | 1265 |
| ed.n_bars_in_range | 1194 |
| event_type_ny_30m | 1181 |
| ctx.day_of_week_et | 910 |
| ed.or_high | 871 |

### orb / `oc.break_low.wick_breached`

_test_auc=0.695, test_acc=0.771 vs majority 0.767_

| feature | gain |
|---|---|
| side_bullish | 5081 |
| ed.or_direction_bullish | 4055 |
| ed.or_range_pts | 2418 |
| side_bearish | 1977 |
| year | 1800 |
| month | 1671 |
| event_type_ny_30m | 1470 |
| day_of_week | 1194 |
| ed.range_minutes | 1072 |
| xd.has_ft_in_24h | 764 |

### ft / `oc.break_low.wick_breached`

_test_auc=0.689, test_acc=0.75 vs majority 0.742_

| feature | gain |
|---|---|
| ed.first_third_range_pts | 2560 |
| side_bearish | 2388 |
| ed.n_1m_bars_in_first_third | 1329 |
| year | 1148 |
| month | 1033 |
| day_of_week | 815 |
| side_bullish | 535 |
| ed.first_third_low | 408 |
| ed.ext_below_low_1x_range | 392 |
| ed.first_third_high | 348 |

### disp / `oc.retracement.tapped_open`

_test_auc=0.672, test_acc=0.744 vs majority 0.734_

| feature | gain |
|---|---|
| ed.ratio_vs_recent_mean | 7260 |
| day_of_week | 4788 |
| ed.body_to_range_ratio | 2137 |
| side_bearish | 1740 |
| ctx.hour_of_day_et | 1734 |
| hour_of_day_utc | 1653 |
| month | 1621 |
| ctx.day_of_week_et | 1527 |
| year | 1424 |
| event_type_1h_disp | 894 |

### swing / `oc.breakout.wick_taken`

_test_auc=0.671, test_acc=0.721 vs majority 0.698_

| feature | gain |
|---|---|
| ctx.hour_of_day_et | 9941 |
| hour_of_day_utc | 8063 |
| day_of_week | 7855 |
| ed.tracking_timeframe_1h | 4270 |
| side_high | 3849 |
| month | 2896 |
| year | 2791 |
| ctx.day_of_week_et | 2429 |
| ed.tracking_timeframe_4h | 1574 |
| event_type_pivot_5_1h | 1086 |

### ob / `oc.invalidation.invalidated`

_test_auc=0.664, test_acc=0.811 vs majority 0.808_

| feature | gain |
|---|---|
| ed.confirms_close_gt_ob_high | 3846 |
| ed.ob_body_width_pts | 3030 |
| year | 2790 |
| side_bearish | 2585 |
| ctx.day_of_week_et | 2439 |
| ctx.hour_of_day_et | 2407 |
| month | 2051 |
| ed.ob_range_width_pts | 1883 |
| hour_of_day_utc | 1686 |
| day_of_week | 1496 |

### tp / `oc.next_period.thesis_confirmed`

_test_auc=0.662, test_acc=0.679 vs majority 0.672_

| feature | gain |
|---|---|
| ed.parent_body_pts | 5148 |
| ed.parent_range_pts | 4163 |
| ed.is_bullish_classic_po3 | 1632 |
| month | 1328 |
| year | 1109 |
| ed.parent_close | 1084 |
| ed.parent_open | 1001 |
| ed.parent_low | 951 |
| ed.parent_high | 787 |
| ed.high_sub_period_london | 721 |

### disp / `oc.retracement.tapped_full`

_test_auc=0.658, test_acc=0.703 vs majority 0.693_

| feature | gain |
|---|---|
| ed.ratio_vs_recent_mean | 7090 |
| day_of_week | 5461 |
| hour_of_day_utc | 3043 |
| ctx.hour_of_day_et | 2411 |
| month | 2238 |
| side_bearish | 2019 |
| year | 1882 |
| ctx.day_of_week_et | 1659 |
| ed.body_to_range_ratio | 1502 |
| event_type_1h_disp | 1224 |

### disp / `oc.invalidation.invalidated`

_test_auc=0.648, test_acc=0.667 vs majority 0.649_

| feature | gain |
|---|---|
| ed.ratio_vs_recent_mean | 5936 |
| day_of_week | 4836 |
| side_bearish | 2398 |
| ctx.day_of_week_et | 2032 |
| hour_of_day_utc | 1975 |
| month | 1951 |
| year | 1808 |
| ctx.hour_of_day_et | 1671 |
| ed.body_to_range_ratio | 1480 |
| event_type_1h_disp | 1329 |

### swing / `oc.breakout.close_taken`

_test_auc=0.638, test_acc=0.654 vs majority 0.618_

| feature | gain |
|---|---|
| ctx.hour_of_day_et | 9743 |
| day_of_week | 7112 |
| hour_of_day_utc | 5949 |
| side_high | 5000 |
| ed.tracking_timeframe_1h | 4549 |
| year | 4251 |
| month | 3409 |
| ctx.day_of_week_et | 3220 |
| ed.pivot_price | 1343 |
| side_low | 1265 |

### orb / `oc.broke_both_sides`

_test_auc=0.631, test_acc=0.615 vs majority 0.556_

| feature | gain |
|---|---|
| event_type_ny_30m | 4196 |
| ed.or_range_pts | 3136 |
| xd.has_ft_in_24h | 1860 |
| year | 1624 |
| ed.n_bars_in_range | 1589 |
| month | 1574 |
| day_of_week | 1267 |
| ed.mode_ny_30m | 1139 |
| xd.has_disp_in_24h | 696 |
| ed.ext_above_high_05x | 676 |

### sweep / `oc.forward_continuation.continued`

_test_auc=0.629, test_acc=0.911 vs majority 0.911_

| feature | gain |
|---|---|
| year | 2853 |
| month | 2507 |
| ed.swept_reference.prior_period_label_session_ny | 2283 |
| hour_of_day_utc | 1748 |
| ed.sweep_depth_pts | 1486 |
| side_high | 1442 |
| day_of_week | 1235 |
| ctx.day_of_week_et | 1148 |
| ctx.hour_of_day_et | 1014 |
| ed.swept_reference.level_price | 908 |

### eql / `oc.take.wick_taken`

_test_auc=0.618, test_acc=0.826 vs majority 0.822_

| feature | gain |
|---|---|
| month | 7260 |
| ed.level_price | 7159 |
| side_high | 7061 |
| year | 5795 |
| ed.cluster_min_price | 5029 |
| ed.cluster_mid | 4592 |
| ed.cluster_spread_pts | 4512 |
| ed.cluster_max_price | 3805 |
| hour_of_day_utc | 3044 |
| ed.tolerance_pts | 2813 |

### eql / `oc.take.close_past`

_test_auc=0.567, test_acc=0.774 vs majority 0.771_

| feature | gain |
|---|---|
| side_high | 9413 |
| ed.level_price | 8685 |
| month | 7599 |
| year | 6656 |
| ed.cluster_mid | 5564 |
| ed.cluster_min_price | 5189 |
| ed.cluster_spread_pts | 3834 |
| ed.cluster_max_price | 3818 |
| ed.tolerance_pts | 2375 |
| ed.parent_pivot_mode_pivot_3_1h | 2246 |

### smt / `oc.next_period.primary_took_period_n_high`

_test_auc=0.547, test_acc=0.542 vs majority 0.539_

| feature | gain |
|---|---|
| ed.symbol_states.ES.c.0.reference_low | 125 |
| ed.symbol_states.ES.c.0.reference_high | 122 |
| ed.first_break_price | 100 |
| ed.symbol_states.NQ.c.0.reference_high | 85 |
| ed.symbol_states.YM.c.0.reference_low | 81 |
| day_of_week | 75 |
| ctx.hour_of_day_et | 69 |
| ed.symbol_states.NQ.c.0.reference_low | 62 |
| ed.symbol_states.YM.c.0.reference_high | 53 |
| side_high | 44 |

### smt / `oc.next_period.thesis_confirmed_strict`

_test_auc=0.533, test_acc=0.535 vs majority 0.537_

| feature | gain |
|---|---|
| ed.first_break_price | 269 |
| ctx.hour_of_day_et | 182 |
| day_of_week | 180 |
| ed.symbol_states.NQ.c.0.reference_high | 154 |
| ed.symbol_states.NQ.c.0.reference_low | 152 |
| ed.symbol_states.ES.c.0.reference_low | 149 |
| ed.symbol_states.ES.c.0.reference_high | 142 |
| month | 133 |
| hour_of_day_utc | 131 |
| ed.symbol_states.YM.c.0.reference_high | 87 |

### eql / `oc.take.first_take_was_reversal`

_test_auc=0.529, test_acc=0.506 vs majority 0.504_

| feature | gain |
|---|---|
| ed.level_price | 1254 |
| ed.cluster_max_price | 976 |
| ed.cluster_mid | 858 |
| ed.cluster_min_price | 788 |
| month | 712 |
| year | 499 |
| ed.cluster_spread_pts | 433 |
| side_high | 359 |
| hour_of_day_utc | 159 |
| day_of_week | 136 |

### smt / `oc.n_plus_2.thesis_confirmed_strict`

_test_auc=0.513, test_acc=0.471 vs majority 0.543_

| feature | gain |
|---|---|
| ed.symbol_states.ES.c.0.reference_high | 298 |
| ed.first_break_price | 295 |
| ed.symbol_states.YM.c.0.reference_high | 201 |
| ed.symbol_states.NQ.c.0.reference_low | 194 |
| side_high | 187 |
| ed.symbol_states.NQ.c.0.reference_high | 179 |
| ed.symbol_states.YM.c.0.reference_low | 164 |
| ed.symbol_states.ES.c.0.reference_low | 153 |
| hour_of_day_utc | 125 |
| month | 117 |

### smt / `oc.next_period.primary_took_period_n_low`

_test_auc=0.507, test_acc=0.551 vs majority 0.553_

| feature | gain |
|---|---|
| ed.first_break_price | 149 |
| hour_of_day_utc | 106 |
| ed.symbol_states.ES.c.0.reference_high | 92 |
| ctx.hour_of_day_et | 90 |
| ed.symbol_states.ES.c.0.reference_low | 86 |
| ed.symbol_states.YM.c.0.reference_low | 79 |
| ed.symbol_states.NQ.c.0.reference_low | 59 |
| day_of_week | 55 |
| year | 55 |
| month | 51 |

### ft / `oc.rest_confirms_first_third`

_test_auc=0.484, test_acc=0.513 vs majority 0.513_

| feature | gain |
|---|---|
| side_bullish | 143 |
| month | 86 |
| side_bearish | 86 |
| ed.first_third_range_pts | 74 |
| ed.n_1m_bars_in_first_third | 72 |
| year | 68 |
| ctx.day_of_week_et | 26 |
| ed.ext_above_high_05x_range | 23 |
| ed.ext_above_high_1x_range | 21 |
| ed.first_third_close | 16 |

### ft / `oc.rest_reverses_first_third`

_test_auc=0.473, test_acc=0.487 vs majority 0.494_

| feature | gain |
|---|---|
| side_bearish | 138 |
| month | 100 |
| side_bullish | 100 |
| ed.n_1m_bars_in_first_third | 55 |
| year | 45 |
| ed.first_third_range_pts | 42 |
| hour_of_day_utc | 25 |
| ctx.day_of_week_et | 23 |
| ed.first_third_low | 17 |
| day_of_week | 15 |

