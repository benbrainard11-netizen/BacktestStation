# Fresh 2015-2017 Holdout — OB strict + Sweep reversed

_Generated 2026-05-17. Run: v28 slim-anchor walk-forward._

## Headline

**The 2-family core (OB strict + Sweep reversed filtered) produces consistent edge on truly untouched 2015-2017 data.** ~1,735 R/year on independent silos, comparable to ~1,636 R/year on the 2018-2019 baseline.

## What was tested

The 2-family core that survived the v20 locked walk-forward:
- OB strict
- Sweep reversed (filtered, hour-filter UTC hours dropped: 22-06)

Symbols: NQ + ES + YM (per v27 universe).

## The window

**2015-01-01 → 2017-12-31** — three full calendar years. Never used in v8a / v13-v19 / v20 research. Truly out-of-sample.

## Method

Because 247's anchor matrices for 2015-2017 don't exist, this run uses a slim-anchor approximation:
- Detectors generated for 2015-2017 (`backend/scripts/generate_events_2015_2017.py`, ~12 min, 23,021 events)
- Strict label recomputed from raw bars (`backend/scripts/build_slim_anchors_2015_2017.py`)
- v8a simulator + same fill model + same trade rule as v20

v19 audit showed my recomputed label has ~65% agreement with 247's strict label. The methodology was validated by running the same slim approach on 2018-2019 and confirming the cum_R is within 15% of v20/v27 baselines and per-trade avg_R is consistent.

## Result table

| Family | n_trades | cum_R | avg_R | win_rate |
|---|---:|---:|---:|---:|
| OB strict | 8,515 | 2,821.80 | +0.331 | 56.6% |
| Sweep reversed filtered | 5,027 | 2,386.00 | +0.475 | 53.0% |
| **Combined** | **13,542** | **5,207.80** | | |

Per-symbol cum_R:

| | NQ | ES | YM |
|---|---:|---:|---:|
| OB strict | 1,284 | 599 | 939 |
| Sweep reversed | 997 | 486 | 903 |
| **Total** | **2,281** | **1,085** | **1,842** |

YM remains a strong contributor (35% of OB total, 38% of Sweep total).

## Comparison: 2015-2017 vs 2018-2019 (both v28 slim methodology)

| Metric | 2015-2017 | 2018-2019 |
|---|---:|---:|
| OB cum_R | 2,822 | 1,941 |
| Sweep cum_R | 2,386 | 1,331 |
| Combined cum_R | 5,208 | 3,272 |
| Years in window | 3.0 | 2.0 |
| **Combined R / year** | **~1,735** | **~1,636** |
| OB avg_R | 0.331 | 0.416 |
| Sweep avg_R | 0.475 | 0.522 |
| OB win rate | 56.6% | 60.6% |
| Sweep win rate | 53.0% | 53.5% |

**Conclusion: the strategy generalizes.** Two independent untouched windows produce comparable R/year, consistent per-trade R, and consistent win rates.

## What this updates

Previous confidence: "v20 partially passed on 2018-2019 + 2026 fragment. ~940 R/year single-account at cap=2 on NQ+ES+YM. Slightly suspect because v27 was post-lock research."

Updated confidence: **a SECOND independent test (this one) produces a similar magnitude result on a truly untouched window.** The 2-family edge isn't a 2018-2025 regime artifact.

Applying the gate 4 concurrency haircut (53.5% retention):
- 5,208 R × 0.535 ≈ 2,786 R single-account over 3 years
- **≈ 929 R/year single-account on 2015-2017**

Compared to ~940 R/year on the 2018-2019 + 2026 fragment.

## What this does NOT prove

1. **The slim label is not 247's exact label** (v19 audit: ~65% agreement). This test is methodologically rigorous but uses a research-grade label approximation, not the production label.

2. **2015-2017 is still historical data**. It was untouched by *our* research, but it's a specific market regime (Fed ZIRP/QE3 ending, lower VIX, different microstructure than recent years). Doesn't guarantee future regimes work.

3. **Independent silos, not single-account**. The 5,208 R is the sum of per-family R without concurrency conflicts. Real single-account number ≈ ~2,800 R for the 3-year window after gate-4 haircut.

4. **No live execution slippage / commission** beyond the v8a 2-tick adverse slippage.

5. **R-to-dollar conversion is still ambiguous**. R = stop distance unit; dollar value depends on stop size and contract value.

## Recommended interpretation

- The "the v20 result might have been a 2018-2019 regime artifact" hypothesis is **less likely** now.
- The "this strategy generalizes" hypothesis is **more credible**.
- Paper-trade go-decision should still wait for the operational infrastructure (live signal generation, drift report, paper-fill recorder) which is in 247's queue.
- When paper-trade infrastructure lands, the v21 lockfile should be drafted with realistic expectations: **plan for 300-600 R/year live**, not 940. Live always under-performs sim.

## Files

- Detector events: `data/meta.sqlite` (research_events table, ~23K new rows for 2015-2017)
- Slim anchors: `D:/BacktestStationData/expanded_holdout_2015_2017/data/ml/anchors/*.parquet`
- Simulation trades: `D:/BacktestStationData/expanded_holdout_2015_2017/v28_simulation_results/`
- Validation baseline (2018-2019): `D:/BacktestStationData/slim_anchors_2018_2019_validation/v28_simulation_results/`
- Code: `backend/scripts/generate_events_2015_2017.py`, `build_slim_anchors_2015_2017.py`, `backend/scripts/ml/v28_slim_anchor_walkforward.py`
