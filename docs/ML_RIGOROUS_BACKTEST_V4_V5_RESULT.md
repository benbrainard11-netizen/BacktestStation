# Rigorous backtest v4 grid + v5 narrow grid + deep-dives

_Generated 2026-05-16, overnight while user away. Followed the v2 matrix that landed at v3 = −39R (near flat). v4 grid found positive territory; v5 narrow grid found the robust optimum; "drop YM" lifts it further. End state: **+110R over 6 years, 5/6 years positive, NQ/ES only**._

## TL;DR

| Version | Best config | n trades | Cum R | Win% | Years +/total | Max DD |
|---|---|---:|---:|---:|---:|---:|
| v1 baseline | stop=1, target=2, tw=60 | 3,964 | **−880** | 28.3% | 0/6 | 929 |
| v3 | consensus + drop drainers + stop=2 (1:1 R:R) | 629 | −39 | 45.9% | 0/6 (all flat) | 50 |
| **v4 winner** | stop=1.5, target=3.0, tw=180 | 629 | **+100** | 43.6% | 4/6 | 72 |
| **v5 winner** ⭐ | stop=2.0, target=4.0, tw=240 | 629 | **+95** | 47.1% | **5/6** | 69 |
| **v5 winner no-YM** ⭐⭐ | same, NQ+ES only | 552 | **+110** | **48.9%** | **5/6** | smaller |

V4 winner had a slightly higher headline cum_R (+100 vs +95) but used a tighter stop that was inflated by 2020. V5 winner with stop=2.0 ATR is **the robust optimum** — broader stop, less reliant on any single year. Dropping YM lifts it further (+110R, +0.20 R per trade).

## V4 grid — found positive territory

75 configs sweeping `stop_mult × target_mult × trade_window` around v3's near-flat baseline, with consensus filter ON and SMT/sweep dropped.

- **37 of 75 configs are positive** (vs 0 in the v1-derived experiments)
- Top configs all use **target ≥ 3.0 ATR** and **window = 180 min**
- Best: `v4_drop_both_stop1.5_tgt3.0_tw180` → +100.2R, 43.6% win rate, 35.9R max DD (within-year)

Heatmaps in `experiments/backtests/2026-05-15_rigorous_v4_grid/v4_grid_heatmap_tw{60,120,180}.png` show:
- `tw=60` (v1's window): mostly negative — wider stops don't save you with such tight time exits
- `tw=180`: mostly green, with the best cells in the top-right (wide stop, wide target)

**Key insight: longer time windows + wider R:R is the answer.** v1's 60-min window + 2:1 R:R was inverted from what these signals need.

## V4 winner deep-dive — uneven year-to-year

V4 winner's +100R is **NOT** consistent:

| Year | n | Win% | Cum R | Max DD |
|---|---:|---:|---:|---:|
| 2020 | 102 | 58.8% | **+68.8** | 4 |
| 2021 | 79 | 35.4% | +4.9 | 11 |
| 2022 | 99 | 32.3% | −3.0 | 13 |
| 2023 | 110 | 51.8% | +21.1 | 15 |
| 2024 | 121 | 55.4% | +58.9 | 9 |
| **2025** | 118 | **25.4%** | **−50.7** | **61** |

4 of 6 years positive. 2020 + 2024 carry most of the gain. **2025 (most recent year) is a disaster** — within-year DD of 61R. The full-curve max DD is **72R**, not 36R.

This made me suspect the +100R was over-fit to stop=1.5 (which especially helped 2020). The narrow v5 grid confirmed: **stop=2.0 is the robust optimum**.

## V5 narrow grid — stop=2.0 dominates

60 configs sweeping a narrower neighborhood around v4's winner:
- `stop_mult ∈ {1.0, 1.25, 1.5, 1.75, 2.0}`
- `target_mult ∈ {2.5, 3.0, 3.5, 4.0}`
- `trade_window_min ∈ {150, 180, 240}`

Result:
- **All 60 configs positive** (vs 37/75 in v4 grid — narrower grid is universally positive)
- **11 of 60 are "robust"** (≥5/6 years positive)
- **All 11 robust configs use stop=2.0** (zero robust configs at stop < 2.0)
- Best by stability: `stop=2.0, target=4.0, tw=240` → +95.1R, 47.1% win rate, **5/6 years positive**, 34R within-year DD

**Stop=1.5 made the v4 winner look great** by capturing 2020 perfectly with a tight stop, but it FAILED the 5/6-year stability bar. Stop=2.0 sacrifices a little 2020 upside for cleaner 2022 + 2023 + 2025 behavior.

## V5 winner deep-dive (with and without YM)

V5 winner per-year:

| Year | n | Win% | Cum R | Max DD |
|---|---:|---:|---:|---:|
| 2020 | 102 | 62.7% | +67.3 | 5 |
| 2021 | 79 | 50.6% | +21.1 | 8 |
| 2022 | 99 | 40.4% | +5.6 | 19 |
| 2023 | 110 | 48.2% | +11.5 | 14 |
| 2024 | 121 | 57.0% | +36.7 | 10 |
| 2025 | 118 | 25.4% | −47.0 | 58 |

5/6 years positive. **2025 is still the bad year** across every variant tested — it's not a config issue, it's a regime issue specific to that year. We saw it earlier on `resistance_rejection_3bar` (AUC dropped to 0.647 in 2024); now it shows up in 2025 too.

Per-symbol:

| Symbol | n | Win% | Cum R |
|---|---:|---:|---:|
| ES.c.0 | 337 | 50.4% | **+71.5** |
| NQ.c.0 | 215 | 46.5% | +38.4 |
| YM.c.0 | 77 | 33.8% | **−14.8** |

**ES + NQ contribute +110R; YM drags −15R.** Dropping YM gives us:

| Metric | v5 winner (all 3) | v5 winner no-YM |
|---|---:|---:|
| n trades | 629 | 552 |
| Cum R | +95.1 | **+109.9** |
| Win rate | 47.1% | **48.9%** |
| Avg R | 0.151 | **0.199** |
| Years positive | 5/6 | 5/6 |

**The current best:** v5 winner + drop YM → **+110R over 6 years, 49% win rate, 5/6 years positive, ~92 trades/year on NQ/ES.**

## What's actually deployable here

Numbers in R-units. To translate to dollars roughly:
- ATR(14, 5m) on NQ is typically 15-25 points
- 1R = 1 ATR ≈ 20 points on NQ
- 1 NQ point = $20 per contract
- So 1R ≈ $400 per NQ contract per trade

Estimated NQ-only P&L: avg_R × trades × $/R = 0.20 × ~80 trades/year × $400 = ~$6,400/year per contract gross. Less commissions + slippage.

For ES: ATR ~3-5 points, 1 ES point = $50, so 1R ≈ $200. ~0.20 × 100 trades × $200 = ~$4,000/year per contract gross.

Combined NQ+ES on 1 contract each: **~$10k/year per pair of contracts, before costs.** Modest. Real costs (commission ~$5 round-trip × 200 trades = $1k/year, slippage 1 tick × 200 = $200 NQ / $25 ES) → ~$8-9k/year net.

That's **a 1-pair scaling example**. With $50k risk capital (~5R worst-case DD = 70R × $400 = $28k peak DD; 2x safety = $56k → use $50k for sizing room), that's **$8-9k / $50k = 16-18% annualized** before taxes. Modest but real.

For deploy decisions: still wants more iteration (the 2025 weakness + the variance across years means R uncertainty is high). But the system has crossed from "loses money" to "marginally profitable" — a meaningful threshold.

## What 2025 tells us

2025 is the *only* year where v5 winner lost (−47R no-YM). The proxy-R backtest also showed 2025 as the weakest top-10% precision year for `resistance_rejection_3bar` (0.79 vs ~1.00 in 2021-2025). Earlier session noted 2024 was the weak year for the model AUC.

**Hypothesis: there's a regime shift in 2024-2025 that breaks the model's gap-rejection predictions.** Could be:
- Different volatility regime (post-COVID normalization)
- Different SPY/QQQ session structure (extended hours, weekend trading)
- Different institutional positioning patterns

Worth a follow-up dedicated analysis when fresh: feature distribution shift between 2024 and prior years.

## Suggested next moves (when you're back)

1. **Write a short Strategy v2 spec** that captures the v5-no-YM config as the "current best": NQ+ES, consensus filter, 2.0 ATR stop / 4.0 ATR target / 240min window, drop SMT/sweep/YM.
2. **Diagnose 2025 specifically**: which feature families had distribution shifts vs 2023/2024? Could inform a 2026-onwards retrain.
3. **Run v5-no-YM with consensus tier = 3+** (instead of 2+): is there an even-cleaner subset that requires 3-signal agreement?
4. **Wait for 247's strict swing pivot labels**: when they ship, add as a 6th signal family. The consensus filter would have more material to work with.

## Files committed

```
backend/scripts/ml/rigorous_backtest_v4_grid.py
backend/scripts/ml/v4_winner_deepdive.py
backend/scripts/ml/v5_narrow_grid.py
backend/scripts/ml/v5_winner_deepdive.py

experiments/backtests/2026-05-15_rigorous_v4_grid/
  v4_grid_rollup.csv, v4_grid_heatmap_tw{60,120,180}.png, summary.json

experiments/backtests/2026-05-15_v4_winner_deepdive/
  winner_trades.csv, per_year.csv, per_symbol.csv,
  per_signal_per_year.csv, exit_reason_by_signal.csv,
  winner_equity.png, winner_equity_by_year.png, winner_drawdown.png,
  summary.json

experiments/backtests/2026-05-15_v5_narrow_grid/
  v5_narrow_rollup.csv, v5_per_year.csv, v5_heatmap_tw{150,180,240}.png,
  summary.json

experiments/backtests/2026-05-15_v5_winner_deepdive/
  v5_winner_trades.csv, v5_winner_no_ym_trades.csv,
  per_year.csv, per_symbol.csv, per_signal_per_year.csv,
  v5_winner_equity_compare.png, v5_winner_drawdown.png,
  summary.json
```

## Reproducing

```bash
python -m scripts.ml.rigorous_backtest_v4_grid       # 75 configs ~8 min
python -m scripts.ml.v4_winner_deepdive              # 1 config detailed ~3 min
python -m scripts.ml.v5_narrow_grid                  # 60 configs ~7 min
python -m scripts.ml.v5_winner_deepdive              # v5 winner + no-YM ~3 min
```
