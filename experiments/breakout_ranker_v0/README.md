# breakout_ranker_v0

A fresh, honest build of the breakout strategy from the pasted advice — the exact v0 question,
verbatim:

> *Among liquid stocks in top-quartile sectors, which names are compressing near 52-week highs
> and most likely to reach +2R before -1R after breaking their pivot?*

Built at Ben's explicit request ("rebuild the breakout model anyway") **despite** the lab's
standing finding that breakouts are comprehensively dead (see the equities scorecard in
`stock_strategies_v0`). The point: give the advice its full, fair shot on survivorship-clean
data with the kill-test battery baked in, so the verdict is a clean fresh confirmation either way.

## Construction (faithful to the advice)

- **Universe:** survivorship-CLEAN Polygon common stocks, daily 2016–2026, delisted included
  (`D:\data\processed\stocks\polygon\daily_*.parquet`). Liquid = close ≥ $10, 20-day $vol ≥ $30M.
- **Setup (compression near 52-week high):** close within 8% of the 252-day high and still ≤ pivot
  (in the base, not extended); tight base (pivot−low ≤ 15% over 20 sessions); volatility contracted
  (ATR14 < ATR50); uptrend (close > rising MA50 and > rising MA200).
- **Sector strength:** coarse SIC sector, ranked daily by median trailing-63d return → top-quartile filter.
- **Trade:** pivot = 20-day high; arm a stop-buy at pivot + 0.10·ATR for 10 sessions; stop = pivot − 1·ATR
  (the advice's tradeable R — the base-low stop makes +2R a ~+30% move, a degenerate label).
- **Label:** +2R before −1R within 20 sessions. Honest fills (CLAUDE.md #8): gap-through the stop fills
  at the open (can be worse than −1R), target capped at exactly +2R, stop wins same-bar ties, timeouts
  mark to close. `netR` charges 15 bps round-trip.

## Files

| file | what |
|---|---|
| `common.py` | paths, config constants, clean-universe loader, SIC→sector, sector-strength table |
| `barrier.py` | `arm_and_resolve` — the one shared arm+triple-barrier mechanic (gated AND null use it) |
| `build_setups.py` | detection + causal features + label, plus the matched null-control sample → `out/` |
| `scorecard.py` | the advice's 0–100 candidate score |
| `run_backtest.py` | null control + sector filter + scorecard + robustness (by-year/ex-2020/drop-top/cost) |
| `run_ml.py` | walk-forward LightGBM ranker on the +2R/-1R label + shuffled-label control |
| `sanity_controls.py` | synthetic positive/negative controls proving the barrier + honest fills are correct |

Run with `backend\.venv\Scripts\python.exe -u`.

## Verdict — NO EDGE (dead at every level)

The advice's exact construction has **no tradeable edge**. It is negative even before costs and
worse than a random liquid day in the same stock.

| level | result |
|---|---|
| **Decisive null control** | gated setup net **−0.304R** vs random-liquid-day **−0.212R**; the selection is *worse*; delta>0 in **1/10 years** |
| Sector top-quartile filter | −0.099R vs null — no help (lab's "sector leading hurts" again) |
| Scorecard top-decile | −0.264R; concentrates *losers* (delta>0 in 2/10 yrs; 2022 top-decile −1.12R) |
| ML walk-forward ranker | rank-IC +0.077 is real (shuffled → −0.008) but best decile **loses in 0/8 years**, ex-2020 −0.241, drop-top-1% gross −0.96 |
| Gross (0 bps) | all-gated **−0.144** — negative before any costs; the base rate, not friction, is the killer |

**Why:** the +2R/−1R label has a ~28% win rate vs the ~33% needed to break even at 2:1, and the
gated breakouts come in *below* the random-day base rate. The whole positive tail is a drop-top-1%
fat-tail lottery. A learned ranker can sort "least-bad from bad" but cannot manufacture expectancy
that isn't in the base rate. This independently reproduces the lab's standing breakout null against
the advice's specific spec.

The harness is not the cause: `sanity_controls.py` passes all four honest-fill paths and the
shuffled-label control collapses to base — the mechanic detects signal when it exists; there is none.

**Adversarially verified (4-agent workflow):** detection hand-verified against raw bars (20/20),
null fair (and moot — the strategy loses gross on its own), label/fill/leakage clean (2,000 trades
re-resolved byte-for-byte), and an exhaustive steelman found **no positive pocket** in any slice,
target multiple, or sector. The steelman also caught a real (verdict-neutral) bug — `regime_up`/
`rs_6m` were dead because the CS-only universe filter dropped SPY; **fixed** (SPY is kept through
the filter) and everything re-ran. With working regime/relative-strength the verdict is unchanged.
Notably the advice's own direction is backwards here: strong relative-strength names were the *worst*.

See `LEDGER.md` for the run-by-run record.
