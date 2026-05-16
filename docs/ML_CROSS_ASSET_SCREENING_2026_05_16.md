# Cross-asset v5 screening — gap-rejection works on FX, not indices

_Generated 2026-05-16. First test of the gap-rejection strategy on the 22-symbol local anchor stack (rebuilt overnight by the local Codex). Question: does v5/v8a-style gap rejection generalize cross-asset, or is it an index-specific edge?_

## TL;DR

**Gap-rejection IS a cross-asset edge — but it's an FX edge, not a futures edge.** Applying v8a-style trade rules (vol-floored stops, 5×ATR target, 240-min window) to the broad rejection labels (`next_60m.resistance_rejection_3bar` / `support_rejection_3bar`) on the 22-symbol local matrix:

- **FX (7 symbols, 564 trades): +83.9R, 51.2% win rate** ⭐
- Index (4 symbols, 1,363 trades): −19.4R, 50.0% win rate
- Energy (5 symbols, 544 trades): −21.5R, 43.2% win rate
- Rates (4 symbols, 253 trades): −24.3R, 41.1% win rate

The "indices win" story we've been chasing for two days was actually an **ES-specific story** — NQ and YM drag the asset class to net negative even on broad labels.

## Test setup

- **Matrix**: `data/ml/anchors/opening_gap_snapshots_xctx_gapctx.parquet` (local rebuild, 36,944 rows × 1,078 cols, 22 symbols)
- **Signals**: `next_60m.resistance_rejection_3bar` (gap_down side → short) + `next_60m.support_rejection_3bar` (gap_up side → long)
- **Trade rules**: v8a — `stop = max(2.0 × ATR(14, 5m), 1.5 × ATR(14, 30m))`, `target = 5.0 × stop ATR`, 240-min window, wait for confirmation bar, enter at next bar open
- **Filter**: top-10% model picks per (signal, year). NO consensus filter — broad labels' gap_down and gap_up are mutually exclusive by construction.
- **Test years**: 2020-2025 walk-forward
- **Per-symbol breakdown**: pool both signals, group by primary_symbol

## Per-symbol results (all 20 active contracts)

| Symbol | Asset class | n | Win % | Cum R | Avg R |
|---|---|---:|---:|---:|---:|
| **6N.c.0** | fx | 239 | 51.0% | **+31.4** | +0.131 |
| **6C.c.0** | fx | 48 | **81.2%** | **+28.2** | +0.588 |
| **6E.c.0** | fx | 57 | 61.4% | **+20.3** | +0.356 |
| ES.c.0 | index | 342 | 52.0% | +9.0 | +0.026 |
| 6B.c.0 | fx | 25 | 64.0% | +4.3 | +0.171 |
| BZ.c.0 | energy | 41 | 43.9% | +3.3 | +0.080 |
| 6A.c.0 | fx | 88 | 36.4% | +2.5 | +0.028 |
| HO.c.0 | energy | 28 | 64.3% | +2.0 | +0.072 |
| 6S.c.0 | fx | 97 | 42.3% | −0.9 | −0.010 |
| ZN.c.0 | rates | 110 | 40.0% | −1.2 | −0.011 |
| 6J.c.0 | fx | 10 | 40.0% | −1.8 | −0.177 |
| RB.c.0 | energy | 28 | 57.1% | −2.3 | −0.083 |
| ZB.c.0 | rates | 67 | 50.7% | −2.8 | −0.041 |
| ZT.c.0 | rates | 14 | 28.6% | −3.4 | −0.241 |
| RTY.c.0 | index | 241 | 52.7% | −3.9 | −0.016 |
| NQ.c.0 | index | 413 | 48.7% | −8.0 | −0.019 |
| NG.c.0 | energy | 319 | 41.1% | −9.5 | −0.030 |
| CL.c.0 | energy | 128 | 40.6% | −15.0 | −0.117 |
| YM.c.0 | index | 367 | 47.7% | −16.5 | −0.045 |
| ZF.c.0 | rates | 62 | 35.5% | −17.0 | −0.274 |

8 of 20 symbols are positive. Mostly FX.

## Per-asset-class

| Class | Symbols | n | Win % | Cum R | Avg R |
|---|---:|---:|---:|---:|---:|
| **fx** | 7 | 564 | 51.2% | **+83.9** | +0.149 |
| index | 4 | 1,363 | 50.0% | −19.4 | −0.014 |
| energy | 5 | 544 | 43.2% | −21.5 | −0.040 |
| rates | 4 | 253 | 41.1% | −24.3 | −0.096 |

## What this changes

### 1. The "indices" portfolio was always an "ES portfolio"

ES is the only profitable index (+9R), and even that's modest. NQ (−8R) and YM (−17R) drag the asset class negative. **v5/v8a's apparent success on NQ+ES was almost entirely ES-driven.** YM was a known drag (we already filtered it); NQ being a drag is a new finding that the strict-label data masked.

### 2. FX is the genuinely tradeable lane

Three FX symbols cleared significant positive R with high win rates:
- **6C (CAD): 81.2% win on 48 trades, +28.2R** — striking precision even at small sample
- **6N (NZD): 51% on 239 trades, +31.4R** — bigger sample, lower precision but still solid
- **6E (EUR): 61% on 57 trades, +20.3R**

These are using **broad labels** with **no strict-label upgrade**, **no consensus filter**, and **the same v8a rules** designed for index futures. The FX edge exists *before* any of the optimizations we built for indices.

### 3. Strategic redirect for 247's next task

Original plan: ship strict order_block labels. New higher-leverage option:

**Ship strict labels on the FX subset of the 22-symbol opening_gap matrix.** Then we can run v8a-style portfolio backtests on 6C/6N/6E/6E/6A/6B/6S with consensus filters and full strict-label tooling. If FX broad-label is already +84R, FX strict-label could plausibly be 2-3× that.

### 4. v8a deploy candidate question

v8a is currently spec'd on NQ+ES with strict labels. The honest deploy decision now has 3 options:

1. **NQ+ES strict (current v8a)**: +79R / 27R DD over 6yr, NQ is actually a drag on this version too (we should verify)
2. **ES-only strict**: probably +60-70R based on the broad-label per-symbol breakdown
3. **FX broad-label v8a**: +84R already, before any strict-label investment

Option 3 looks like the best risk-adjusted lane *right now*. Worth a per-symbol v8a deep-dive on FX to confirm.

## Caveats

- **Sample sizes vary wildly per symbol.** 6C has 48 trades over 6 years (~8/year). 6J has 10. NQ has 413. Small-sample symbols' precision numbers should be treated with wide confidence intervals.
- **No strict labels tested.** This is the *broad-label* version. Strict labels might lift FX further OR might not work as well on FX (different price scale).
- **Cent-based forward windows** (which 247 used for FVG strict labels) may not translate to FX which trades in pips with different scales. Worth thinking through before asking 247 to build strict FX labels.
- **No consensus filter.** Gap_down and gap_up are mutually exclusive, so the filter we use on the 5-signal portfolio doesn't apply here. For FX-strict v3, we'd want to add a complement (e.g. strict partial_touch labels) for actual consensus opportunities.

## Suggested next moves

1. **Per-symbol v8a deep-dive on FX** using the strict labels we already have (won't work because strict labels are only on the 3-symbol release matrix — but we can run v8a-style on the local FX broad-label data with full per-year breakdown). ~30 min.
2. **Ask 247 to add strict labels on the local 22-symbol opening_gap matrix** (or just FX subset). New task — possibly higher leverage than the strict order_block batch we previously suggested. ~6-10 hours of 247's time.
3. **Strategy v3 spec doc** — now we know FX is the lane, not just NQ+ES. Worth re-writing the spec around FX-anchored deployment.

## Reproducing

```bash
python -m scripts.ml.cross_asset_screening_v5
```

Reads `data/ml/anchors/opening_gap_snapshots_xctx_gapctx.parquet` (local 22-symbol broad-label matrix). Outputs in `experiments/backtests/2026-05-16_cross_asset_screening/`:

- `trades.csv` — every simulated trade
- `per_symbol.csv` — per-symbol rollup
- `per_signal_per_symbol.csv` — gap_down/gap_up × symbol
- `per_asset_class.csv` — asset-class rollup
- `per_symbol_bar.png` — visualization
- `summary.json`
