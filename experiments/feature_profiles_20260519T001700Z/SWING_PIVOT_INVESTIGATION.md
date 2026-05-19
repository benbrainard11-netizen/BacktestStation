# swing_pivot — investigation of the "3-5x MFE/MAE ratio" anomaly

_Generated 2026-05-18. Followup from `experiments/feature_profiles_20260518T190231Z/`._

## Headline

The "swing_pivot fwd10 MFE/MAE ratio = 3.3-4.7" finding from the v30 baseline was **a structural artifact, not a tradable edge**. But fixing the metric revealed a *different* finding that IS real: swing_pivot has a 65-67% directional hit rate at the 10-bar horizon — substantially better than OB / FVG / Sweep (49-50%, coin flip).

So both statements are simultaneously true:
- The MFE/MAE ratio is meaningless for swing_pivot (don't compare to other detectors on this metric).
- swing_pivot's directional thesis (high → bearish, low → bullish) does play out more often than chance.

## Why the MFE/MAE ratio is structural for swing_pivot

The detector fires AT the swing extreme. For a swing HIGH:
- `reference_close` = the close at the swing high bar
- `thesis_direction` = "down" (the swing high is resistance; thesis is rejection)
- `mae_pts_against_thesis` = how much price went UP relative to ref_close in next N bars

Because the swing high IS the local maximum by definition, price rarely exceeds the high immediately after. **44% of swing_pivot events have MAE ≤ 0.001 in the next 10 bars** vs only 1.3% for order_block.

Meanwhile MFE (price moving DOWN from a swing high) is unbounded — typical 5-50 points.

So `mean(MFE) / mean(MAE)` = (substantial number) / (near-zero number) = inflated ratio. Not because the detector is right; because the math is asymmetric by construction.

## Per-detector MAE distribution comparison (2024 sample)

| Detector | mean MAE | median MAE | % with MAE ≈ 0 |
|---|---:|---:|---:|
| swing_pivot | 8.26 | 0.0024 | **44%** |
| order_block | 17.97 | 0.078 | 1.3% |
| fvg_formation | similar | similar | ~2% |

The median MAE difference is 30x. That's the artifact.

## The real edge: directional hit rate

After fixing v30 to derive `last_close - reference_close` for swing_pivot (its outcomes JSON is missing the precomputed `last_close_vs_reference_pts` field that other detectors have), the directional hit rate per asset class:

| Detector | bond | energy | fx | grain | index |
|---|---:|---:|---:|---:|---:|
| **swing_pivot** | **0.652** | **0.653** | **0.668** | **0.663** | **0.649** |
| order_block | 0.482 | 0.499 | 0.499 | 0.489 | 0.496 |

swing_pivot: 65-67% across all classes.
order_block: 48-50% (essentially 50/50).

**This is a real, robust signal.** The thesis (swing high → bearish, swing low → bullish) plays out 2/3 of the time at the 10-bar horizon.

## Catch: hit rate ≠ profitable strategy

A 65% hit rate is impressive but says nothing about magnitude. If the 65% wins are small and the 35% losses are large, expected value can still be negative. The MFE/MAE ratio (when correctly interpreted) would tell us about magnitude — but it's structurally broken for swing_pivot specifically.

To turn this into a tradable signal, we'd need:
1. Set a stop (e.g., 1 ATR away from pivot in adverse direction)
2. Set a target (e.g., 2 ATR in thesis direction)
3. Re-run forward-test with explicit R units (stop_distance = 1 R)
4. Measure expected R per trade, not just hit rate

This is what v8a does for OB / Sweep. Running v8a on swing_pivot with strict label = swing-was-broken-vs-held would tell us if the 65% hit rate has tradable magnitude.

Note: this is partially what v20 tested. `Swing reversed` was one of the 4 families in v20 and showed:
- 2018-2019 holdout 1: NEGATIVE -1,968 R cum_R
- 2026 holdout 2: NEGATIVE -76 R

So v20 said the swing_pivot trade rule (with v8a stops/targets) is NOT profitable. But that was a reversed-direction test. The 65% directional hit rate found here might suggest natural-direction (high→down, low→up — which is the spec's thesis) IS the right way to use this signal, not reversed.

## Followup: v8a natural-direction backtest on swing_pivot

If swing_pivot has 65% hit rate in thesis direction (per v30 outcomes), and v8a was tested in REVERSED direction (per v20 lockfile: `direction_reversed: true`), then maybe the *unreversed* swing_pivot would be profitable. Worth a v8a re-run with `direction_reversed: false`.

## Fixes shipped to v30

1. **`metric_reliability` column added per profile row.** Values:
   - `pivot_anchored__mae_inflated` — swing_pivot, equal_levels (MAE structurally near-zero)
   - `reactive__comparable` — OB, FVG, sweep, displacement, etc.

2. **`last_close_vs_reference_pts` fallback**: when the outcomes JSON
   doesn't have this field (swing_pivot's case), derive it from
   `last_close - reference_close`.

3. **Hit-rate field now populates for swing_pivot** (was NaN in the baseline).

## Files

- `per_feature_per_symbol.csv` — now includes `metric_reliability` column
- `per_asset_class.csv`
- `SUMMARY.md`
- This investigation note
