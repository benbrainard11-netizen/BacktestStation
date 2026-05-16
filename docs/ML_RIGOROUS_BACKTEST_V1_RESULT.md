# Rigorous OHLCV backtest v1 — result

_Generated 2026-05-16. First end-to-end conversion of the 5-signal portfolio into real dollar-equivalent trades using actual NQ/ES/YM 1m bars. Brutally honest result: **v1 design rules don't translate the model's precision edge into tradeable P&L.**_

## TL;DR

The portfolio loses **−880R over 6 years** (2020-2025) across 3,964 executed trades. **Only one of five signals is positive (ogap_gap_down_rejection, +30R / 6 years).** The biggest precision signal (SMT 100% top-10%) becomes the worst tradeable performer; the biggest volume signal (sweep, ~480 picks/year) is the largest drain.

**The 95-100% top-10% label precision we celebrated does NOT survive the conversion to a fixed-R trade with confirmation-bar entry.** This is a real finding, not a bug. The v1 design choices need to be revisited.

## Design (locked-in v1 per user-confirmed answers to STRATEGY_V1_DRAFT)

| # | Choice | Value |
|---|---|---|
| Q1 | Universe | NQ + ES + YM, no per-symbol special handling |
| Q2 | Entry | First confirmation bar after fire_ts (red for shorts, green for longs); enter at next bar's OPEN |
| Q3 | Stop/target | Fixed-R: 1 ATR(14, 5m) stop, 2 ATR target (2:1 R:R) |
| Q4 | Time exit | 60 min after entry; mark P&L at actual close |
| Q5 | Consensus filter | None — single-signal picks (user override of multi-year analysis) |
| Q6 | Resistance def | Moot in v1 (only matters for structure stops) |

## Per-signal results

All 6 test years (2020-2025) walk-forward, all 3 symbols pooled, top-10% picks per signal.

| Signal | n trades | Win rate | Cum R | Avg R | Avg win R | Avg loss R | Max DD R |
|---|---:|---:|---:|---:|---:|---:|---:|
| **ogap_gap_down_rejection** | 231 | **39.8%** | **+30.2** | +0.131 | +1.74 | −0.93 | 26.1 |
| ogap_gap_up_rejection | 286 | 39.5% | −5.0 | −0.017 | +1.37 | −0.92 | 41.6 |
| ogap_strict_partial_touch | 515 | 36.1% | −17.6 | −0.034 | +1.56 | −0.94 | 69.7 |
| smt_pd_high_thesis | 69 | 20.3% | −30.5 | −0.442 | +1.70 | −0.99 | 32.5 |
| **sweep_failed_recovered_all** | 2,863 | 25.1% | **−857.6** | −0.300 | +1.73 | −0.98 | 862.6 |
| **POOLED** | **3,964** | **28.3%** | **−880.4** | **−0.222** | — | — | **929.3** |

Required win rate for breakeven (with avg_win ≈ +1.7R, avg_loss ≈ −0.95R): roughly 35-36%. Only `ogap_gap_down_rejection` clears that bar.

## Per-year results

| Year | n trades | Win rate | Cum R | Avg R | Max DD R |
|---|---:|---:|---:|---:|---:|
| 2020 | 645 | 33.6% | −60.9 | −0.094 | 157.2 |
| 2021 | 664 | 26.4% | −184.0 | −0.277 | 191.5 |
| 2022 | 664 | 26.5% | −173.1 | −0.261 | 179.7 |
| 2023 | 663 | 29.7% | −116.2 | −0.175 | 141.5 |
| 2024 | 669 | 32.4% | −106.1 | −0.159 | 140.5 |
| **2025** | 659 | 21.4% | **−240.1** | **−0.364** | 241.7 |

Every year is negative. **2025 is the worst year** — coincidentally the year where the proxy R-backtest showed 100% top-10% precision on gap_down rejection alone (v1 [single-year](ML_BACKTEST_RESISTANCE_REJECTION_V1.md)). The cleanest proxy year is the worst rigorous year. Worth understanding.

## What went wrong — diagnosis

The model evaluation said:
- `resistance_rejection_3bar` label: **95% mean top-10% precision** across 6 years
- `n1_thesis_confirmed_strict` (SMT): **100% precision every year**
- `sweep_failed_recovered`: **77-83% top-10% precision**

The trading rule converts those to:
- gap_down rejection: 40% win rate (modest)
- SMT: 20% win rate (terrible)
- Sweep: 25% win rate (drains R)

**Three likely culprits:**

1. **Label precision ≠ trade precision.** The label says "the 3-bar rejection pattern formed in the next 60m." That's true. But the *price action that forms the pattern* may include 5-15 points of adverse motion FIRST (the move that brought price to the rejection level), then 3 bars of reversal. Our 1 ATR stop gets tagged by that adverse motion before the reversal completes.

2. **Wait-for-confirmation kills the entry.** The confirmation bar approach enters AFTER the first sign of the move. By then, the rejection is partway through. Stops have less room before they're hit. The 60-min window from fire is now shorter (e.g., 50 min) and the rejection may have already played out.

3. **1 ATR(14, 5m) stop is too tight.** ATR(14, 5m) on NQ at 19000 is ~10-20 points — roughly 1-3 minutes of normal price action. Random intraminute noise during the 60-min window can hit that stop without invalidating the thesis.

The SMT signal is especially telling: its label predicts "the period-close thesis was confirmed strictly" — meaning the next-period close moved with the thesis. That's a 1-day-ahead label predicting a slow drift. Applying a 60-minute fixed-R trade rule to a 1-day signal forces us to *exit before the predicted drift completes.* No wonder 80% of SMT trades stop out.

## Why sweep is the biggest drainer

Sweep accounts for 72% of trade volume (2,863 of 3,964) and 97% of the cum-R loss (−858 of −880). The signal predicts "a swept level will fail to hold and recover" — a mean-reversion bet. But the *fire time* is the moment the level just got swept, which is by definition a moment of momentum. Entering a contrarian trade at that moment, with a 1 ATR stop, and waiting for a confirmation bar = entering at the worst possible local volatility.

Per-symbol breakdown of sweep on the proxy test showed it works almost identically well across NQ/ES/YM (77-80% top-10% precision). The rigorous result shows the conversion to P&L drains all three contracts roughly equally.

## What this changes about the next moves

This is a **valuable negative result**. We now know:

1. **Label precision is NOT a sufficient condition for tradeable edge.** The proxy R-curve (+1R / −1R) was an over-simplification. Real trading rules destroy the apparent edge.
2. **The conversion problem is hard.** Going from "model is right 95% of the time" to "a 1 ATR stop / 2 ATR target trade is profitable" requires careful design choices we got wrong on the first attempt.
3. **gap_down rejection is the only signal that survives v1 rules.** Even it's only +30R / 6 years = +5R/year per symbol — too small to deploy with real money, but the only positive contributor.

## v2 design ideas (ordered by my suspicion of impact)

1. **Skip the confirmation bar — enter at the close of the bar at fire_ts.** Fast entry, more room before stop. Tests whether "wait for confirmation" was the killer.
2. **Widen the stop to 2 ATR** (1:1 R:R or 2 ATR stop / 3 ATR target). Eliminates noise stops. Tests whether stop tightness was the killer.
3. **Shorter time exit — 30 minutes.** Faster cash recycling, less time for stops to randomly hit.
4. **Structure-based stop for ogap rejection.** Stop above the gap edge (the actual resistance being rejected), not 1 ATR above entry. Tests whether ATR-based stops are wrong for these signals.
5. **Per-signal rule sets.** SMT's 1-day signal needs a 1-day exit (or just don't trade it intraday). ogap rejection's intraday signal works at intraday horizons. Don't force one rule on all.
6. **2-signal consensus filter.** The multi-year consensus analysis showed +9 pp precision lift. With a fixed-R rule that's only profitable at win rate ≥ 36%, a 9 pp lift might push more signals over the breakeven line.

## Suggested v2 sequence

a. **v2a** = v1 + "enter at close of fire_ts bar" (no confirmation). Tests the entry-timing hypothesis cheapest.

b. **v2b** = v1 + "1:1 R:R with 2 ATR stop" (wider stop). Tests the stop-tightness hypothesis.

c. **v2c** = v1 + consensus filter (2+ signals required). Tests whether better precision overcomes the conversion loss.

If any of a/b/c flips the result to positive, that's the design lever to investigate further. If all three fail too, the issue is deeper than v1 rule choices — the labels themselves may not encode tradeable patterns at the chosen horizons.

## What v1 is worth, despite losing money

This is the first time we converted ML signals into rigorous OHLCV-backed trade simulations. The infrastructure is now in place:

- `BarsCache` loader for fast in-memory 1m bar lookup
- Bar-count-based ATR (handles maintenance breaks, weekends, holidays)
- Trade simulator with confirmation entry, stop/target/time-exit logic
- 6-year walk-forward harness across 5 signals

v2 will reuse all of this. Rerunning with different design choices is now a 3-5 minute job, not a 6-hour build.

## Reproducing

```bash
python -m scripts.ml.rigorous_backtest_v1
```

Outputs in `experiments/backtests/2026-05-15_rigorous_v1/`:

- `all_picks.csv` — top-10% picks per (signal, year)
- `trades.csv` — one row per simulated trade with entry/stop/target/exit details
- `per_signal_stats.csv`
- `per_year_stats.csv`
- `per_signal_equity.png` — equity curve per signal
- `pooled_equity.png` — combined portfolio equity over time
- `summary.json`
