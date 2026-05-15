# FVG strict labels by event_type — does splitting timeframes help?

_Generated 2026-05-15. Source: 20-config sweep on the FVG strict matrix (4 labels × 5 event_type filters)._

## TL;DR

**No.** Filtering the FVG strict matrix by `event_type` (`15m_fvg` / `1h_fvg` / `4h_fvg` / `daily_fvg`) does **not** unhide any signal that the mixed `all` filter was missing. The FVG strict labels are weak across every timeframe — the timeframe mix isn't the problem, the labels themselves are.

## Sweep results

GPU XGB walk-forward, side=all, snapshot=at_fire. The 4 labels are those 247 promoted to the FVG walk-forward summary in commit `1909d5f`.

| Label | 15m_fvg (n=154k) | 1h_fvg (n=40k) | 4h_fvg (n=12k) | daily_fvg (n=2.8k) | all (n=209k) |
|---|---:|---:|---:|---:|---:|
| `forward_10c.after_tap_failed_1x_against` | AUC 0.720, lift +0.14 | 0.718, +0.11 | 0.703, +0.13 | 0.675, +0.16 | **0.719, +0.14** |
| `no_touch_continuation` | 0.725, +0.10 | 0.696, +0.07 | 0.660, +0.07 | **0.373, −0.04** | **0.719, +0.09** |
| `forward_10c.after_tap_1x_clean` | 0.687, +0.08 | 0.719, +0.10 | 0.681, +0.07 | 0.589, +0.07 | **0.695, +0.08** |
| `tap_wick_rejected` | 0.534, +0.04 | 0.533, +0.05 | 0.510, ≈0 | 0.537, +0.04 | **0.532, +0.03** |

For reference, the strongest FVG strict label (forward_10c.after_tap_failed_1x_against on the full mix) lift is +0.136 — vs the strongest opening_gap strict label (next_60m.partial_touch_rejected, all-side) at **+0.549**. That's a **4× gap** in actionable lift, which timeframe-splitting does not close.

## What the data says

- **`15m_fvg` ≈ `all`** — because 15m events are 74% of the FVG matrix, the "all" filter is essentially a 15m filter with extra noise. Splitting them gains nothing.
- **Smaller timeframes don't help.** 4h_fvg and daily_fvg have small sample sizes (12k and 2.8k rows respectively, → ~2k and ~500 per fold) and produce **noisier** numbers, not stronger ones. The daily_fvg `no_touch_continuation` AUC of 0.373 is worse than random because the test set is too small for stable estimation.
- **The one "win"** — daily_fvg / `forward_10c.after_tap_failed_1x_against` at lift +0.160 — is on 2,788 rows and is within fold-to-fold sampling variance. Don't chase it.

## What this means for 247's labeling work

The original suggestion (split FVG by timeframe) is **NOT the fix**. The actual diagnosis is one of:

1. **Label semantics are too weak.** FVG reaction outcomes might just be inherently less predictable than opening-gap reactions. FVGs form often, vary widely in size/strength, and reactions to them have many competing influences (volume, trend, surrounding levels). Opening gaps are a more well-defined daily event with clearer reference levels.
2. **Cent-based forward windows may not map well to futures.** `forward_3c` / `forward_10c` / `forward_50c` use small absolute thresholds. On NQ at ~0.25 tick size, 10c is 0.4 ticks — sub-tick noise. Worth re-running the FVG strict-label generator with windows defined in **points or ATR**, not cents.
3. **The feature pool may not include FVG-specific predictors.** The matrix has xctx + fvggeom + obgeom layers, but a "this tap will reject" model may need features the current pipeline doesn't compute (e.g. "is this FVG near a higher-timeframe pivot?", "what was the volume profile inside the FVG before it formed?").

**Recommended next step for 247**: skip the timeframe split. Instead, take the strongest opening_gap strict patterns (`partial_touch_rejected`, `unfilled_clean_continuation` at 60m/240m horizons with lifts ~+0.5) and try them on FVG with the **same horizon shape**. If `fvg.next_60m.partial_touch_rejected` works better than `forward_10c.after_tap_*`, the issue is window semantics, not features. If it doesn't, the issue is deeper.

## Reproducing

```bash
python -m scripts.ml.fvg_per_timeframe_sweep
```

Reads `D:\BacktestStationData\strategy_lab_core_2026_05_15_strict_reactions\data\ml\anchors\fvg_snapshots_xctx_fvggeom_obgeom_strict.parquet`, runs 20 configs (4 labels × 5 event_types), writes `experiments/gpu_runs/2026-05-15_fvg_per_timeframe/scoreboard.csv`.
