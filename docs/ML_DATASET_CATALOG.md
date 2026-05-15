# ML dataset catalog

_Generated `2026-05-15T16:30:05.693712+00:00`._

## Summary

| item | value |
|---|---|
| research_events rows | 4,158,076 |
| registered detectors | 15 |
| registered outcome computers | 15 |
| feature matrices | 14 |
| snapshot-builder anchor coverage | - |
| catalog json | C:\Users\benbr\BacktestStation-assets-expanded-v1\data\ml\catalog\ml_dataset_catalog.json |

## What Already Exists

- The repo already has registered concept detectors and matching outcome modules.
- `data/ml/features` contains per-detector feature matrices for the registered concepts.
- Snapshot/as-of coverage currently exists for none.
- SMT has richer `at_fire` plus `at_period_close` matrices; generic non-SMT coverage currently starts with conservative `at_fire` snapshots.
- The model leaderboard and walk-forward reports now cover multiple anchor concepts, including opening gaps and live-style forming volume profile.

## Feature Matrices

| short | feature_name | rows | cols | ed | oc | binary_oc | xd | db_outcomes | min | max |
|---|---|---|---|---|---|---|---|---|---|---|
| fvg | fvg_formation | 1,243,757 | 124 | 23 | 75 | 0 | 14 | 100.0% | 2018-05-01 | 2026-04-24 |
| fvp | forming_volume_profile | 1,132,868 | 495 | 47 | 422 | 0 | 14 | 100.0% | 2018-04-30 | 2026-04-24 |
| swing | swing_pivot | 345,702 | 73 | 14 | 33 | 0 | 14 | 100.0% | 2018-05-01 | 2026-04-24 |
| sweep | liquidity_sweep | 237,569 | 82 | 20 | 33 | 0 | 14 | 100.0% | 2018-04-30 | 2026-04-24 |
| ob | order_block | 198,069 | 297 | 38 | 230 | 0 | 14 | 100.0% | 2018-04-30 | 2026-04-28 |
| itr | interval_true_range | 190,192 | 143 | 78 | 38 | 0 | 14 | 100.0% | 2018-05-01 | 2026-04-24 |
| disp | displacement_candle | 187,595 | 91 | 20 | 45 | 0 | 14 | 100.0% | 2018-05-01 | 2026-04-24 |
| vp | volume_profile | 183,662 | 212 | 42 | 144 | 0 | 14 | 100.0% | 2018-04-29 | 2026-04-24 |
| orb | opening_range_breakout | 158,941 | 99 | 21 | 53 | 0 | 14 | 100.0% | 2018-04-30 | 2026-04-24 |
| tp | time_profile | 105,819 | 84 | 26 | 32 | 0 | 14 | 100.0% | 2018-04-29 | 2026-04-23 |
| psp | psp_candle_divergence | 73,278 | 232 | 134 | 72 | 0 | 14 | 100.0% | 2018-05-01 | 2026-04-24 |
| ft | first_third_range | 52,791 | 97 | 20 | 52 | 0 | 14 | 100.0% | 2018-05-01 | 2026-04-24 |
| ogap | opening_gap_levels | 36,944 | 210 | 18 | 166 | 66 | 14 | 100.0% | 2018-04-29 | 2026-04-23 |
| smt | smt_htf_reference_divergence | 10,889 | 301 | 224 | 49 | 2 | 14 | 100.0% | 2018-05-02 | 2026-04-23 |

## Anchor / Model Artifacts

| artifact | kind | rows | cols | snapshots | status_counts |
|---|---|---|---|---|---|

## Gaps To Fill

| gap | items |
|---|---|
| missing feature matrix | equal_levels |
| missing outcome computer | none |
| missing SMT snapshot event type | previous_day_smt, weekly_smt |
| missing snapshot builder | displacement_candle, first_third_range, forming_volume_profile, fvg_formation, interval_true_range, liquidity_sweep, opening_gap_levels, opening_range_breakout, order_block, psp_candle_divergence, smt_htf_reference_divergence, swing_pivot, time_profile, volume_profile |

## Recommended Next Build

The highest-leverage missing piece is **generic snapshot-builder coverage** for the remaining non-SMT concepts. The raw feature matrices exist, but they are event-time rows. The RTX-ready training database should be built from audited as-of snapshots so models can safely combine concepts without look-ahead leakage.

Suggested order:

1. Add period-close snapshot builders for `liquidity_sweep`, `fvg_formation`, `displacement_candle`, and `order_block`.
2. Add neutral future-response labels shared across anchors: forward return, MFE, MAE, took prior high/low, volatility expansion, and time-to-touch.
3. Partition snapshot outputs by `anchor=<concept>/event_type=<type>/year=<year>` once the per-concept schemas stabilize.
4. Re-run this catalog after every matrix generation so the RTX training box can discover datasets from one manifest instead of hard-coded paths.
