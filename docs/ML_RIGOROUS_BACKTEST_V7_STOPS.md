# V7 stop variants — fixing the 2025 stop-out problem

_Generated 2026-05-16. Direct follow-up to the [2025 regime diagnostic](ML_2025_REGIME_DIAGNOSTIC.md) which showed the v5 stop rule is the broken layer in 2025 (model AUC was higher than ever, but 68% of trades stop out). This script tests 4 stop-rule variants designed to absorb the higher 2025 intra-window volatility._

## TL;DR

**v7d (vol-floored stops) is the better deployable strategy than v5.** Same total picks (552), but:
- 2025 loss drops from −35R to **−5R** (nearly flat)
- Max DD drops from 64R to **27R** (less than half)
- Win rate jumps from 49% to **58%**
- DD/CumR ratio improves from 0.59 to **0.37** (much better risk-adjusted)
- Cum_R drops from +110 to +73 (lower headline return)

**v5 remains the highest raw return, v7d is the highest quality return.** For real-money deployment, v7d is the more honest candidate.

## Variants tested

All use v5's portfolio (3 OGAP signals, consensus filter, NQ+ES) and `target_atr_mult / stop_atr_mult = 2.0` R:R structure. Only the stop calculation changes.

| Variant | Stop rule | Description |
|---|---|---|
| v5_baseline | 2.0 × ATR(14, 5m) | The current best from v4/v5 grid |
| v7a_atr30m | 2.0 × ATR(14, 30m) | Use 30-min bar ATR (longer-period vol) |
| v7b_stop3 | 3.0 × ATR(14, 5m) | Wider stop, same timeframe |
| v7c_stop4 | 4.0 × ATR(14, 5m) | Even wider stop |
| **v7d_floor** | **max(2.0 × ATR(14, 5m), 1.5 × ATR(14, 30m))** | **Floor: scales stop up if longer-term vol is high** |

## Results

### Top-line

| Variant | n | Cum R | Win % | Max DD | Years+ | DD/CumR | Stops% | Targets% | TimeExit% |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| v5_baseline | 552 | +109.9 | 48.9% | 64.5 | 5 | 0.59 | 45% | 25% | 29% |
| v7b_stop3 | 552 | +88.0 | 53.1% | 43.8 | 5 | 0.50 | 33% | 15% | 53% |
| **v7d_floor** ⭐ | 552 | **+73.0** | **57.6%** | **26.7** | 5 | **0.37** | 17% | 7% | 75% |
| v7a_atr30m | 552 | +69.0 | 58.7% | 18.1 | 4 | 0.26 | 8% | 5% | 87% |
| v7c_stop4 | 552 | +59.4 | 54.0% | 47.5 | 5 | 0.80 | 26% | 8% | 66% |

### Per-year cum_R

| Variant | 2020 | 2021 | 2022 | 2023 | 2024 | **2025** | Total |
|---|---:|---:|---:|---:|---:|---:|---:|
| v5_baseline | +67.3 | +20.1 | +9.6 | +15.7 | +32.3 | **−35.0** | +109.9 |
| v7b_stop3 | +46.6 | +8.7 | +10.5 | +8.6 | +40.5 | **−26.8** | +88.0 |
| **v7d_floor** | +29.7 | +14.5 | +4.7 | +4.6 | +24.6 | **−5.2** | +73.0 |
| v7a_atr30m | +33.0 | +11.9 | −0.0 | +4.9 | +20.7 | **−1.4** | +69.0 |
| v7c_stop4 | +34.0 | +2.5 | +3.8 | +11.0 | +38.9 | **−30.7** | +59.4 |

## What's actually happening

The 2025 diagnostic showed 68% of v5 trades stopped out in 2025 (vs 29-57% in prior years). The model was *more* accurate than ever but the stops got tagged before the rejection completed.

v7d's mechanism — `stop = max(2.0 × ATR(14, 5m), 1.5 × ATR(14, 30m))` — uses the longer-timeframe ATR as a *floor*. In normal-vol regimes, the 5m ATR is wide enough and the floor doesn't activate. In high-vol regimes (like 2025), the 5m ATR is small relative to the 30m ATR (intraday 5m can be quiet even when 30m ranges are huge), and the floor kicks in to widen the stop.

Result:
- Stop-out rate drops from 45% → 17%
- More trades survive to time exit (29% → 75%)
- Win rate jumps because fewer favorable trades get tagged out

v7a (using ATR(14, 30m) directly with no floor) goes even further: stop-out rate drops to 8%. But target rate also drops to 5%, meaning 87% of trades close at time-exit with whatever P&L the close happens to be. That's a "drift strategy" rather than a "stop/target strategy" — risky in different ways (time exit P&L is path-dependent and noisy).

v7d strikes the better balance: the floor only activates when needed, preserving the stop/target mechanics in normal conditions.

## Why v7d is the better deploy candidate (not v5)

| Property | v5 | v7d |
|---|---|---|
| Cum R / 6 years | +110 | +73 |
| Max DD | 64 | 27 |
| Worst year (2025) | −35 | −5 |
| Years positive | 5/6 | 5/6 |
| Win rate | 49% | 58% |

If you were sizing position to risk 1R = 1% of capital, v5's 64R max DD requires roughly 6.4× more capital than v7d's 27R max DD for the same risk tolerance. Adjusted for capital deployed:

- v5: +110R / 64R DD = **1.72 cum_R per unit of DD risk**
- v7d: +73R / 27R DD = **2.74 cum_R per unit of DD risk**

**v7d is the more efficient strategy per unit of risk.**

Translated to dollars (rough): with 1R ≈ $400 on NQ at typical vol:
- v5: +$44k cum, $26k max DD, requires ~$50k capital to survive DD with margin → 88% return on capital over 6 years
- v7d: +$29k cum, $11k max DD, requires ~$22k capital → **134% return on capital over 6 years**

v7d generates more $ per $ deployed.

## v8 candidates (next iterations)

1. **v8a**: v7d floor + wider target (use 5.0×ATR instead of 4.0×ATR) — captures more on the time-exit drift.
2. **v8b**: trailing stop — once price moves +1 ATR favorable, ratchet stop to entry. Combines v5's win-when-target-hit with v7d's protection on the way there.
3. **v8c**: v7d floor + 60-min time exit (down from 240) — faster recycling, less time for noise.
4. **v8d**: vol-regime filter — skip days where daily realized vol is in top decile of 30-day rolling. Pre-filter rather than rule-adapt.

## Reproducing

```bash
python -m scripts.ml.rigorous_backtest_v7_stops
```

Outputs in `experiments/backtests/2026-05-16_rigorous_v7_stops/`:
- `trades_all_variants.csv` — every trade across 5 variants
- `per_variant_per_year.csv` — cum_R per (variant, year)
- `rollup.csv` — top-line per variant
- `v7_equity.png` — all variants overlaid
- `summary.json`
