# tsfm_milk_v0 — Iteration 0 Dataset Audit

Generated: 2026-05-27T18:46:32.821893+00:00

Resolves PLAN.md §9 ambiguities. Pre-requisite for build_dataset.py.

---

## 1. Bar coverage gaps

**Status:** auto-resolved

**Summary:** Inspected 36 (symbol, year) cells. 21 severely incomplete days flagged. Expected ~390 RTH bars/day (Mon-Fri 13:30-20:00 UTC); anything <200 likely a holiday or market disruption.

**Per-(symbol, year) bar coverage:**

| symbol | year | n_days | <200 RTH | <50 RTH | median RTH bars/day | status |
|---|---|---|---|---|---|---|
| ES.c.0 | 2018 | 173 | 3 | 1 | 391 | ok |
| ES.c.0 | 2019 | 255 | 1 | 0 | 391 | ok |
| ES.c.0 | 2020 | 256 | 3 | 1 | 391 | ok |
| ES.c.0 | 2021 | 255 | 1 | 0 | 391 | ok |
| ES.c.0 | 2022 | 255 | 1 | 0 | 391 | ok |
| ES.c.0 | 2023 | 255 | 2 | 1 | 391 | ok |
| ES.c.0 | 2024 | 256 | 1 | 0 | 391 | ok |
| ES.c.0 | 2025 | 255 | 2 | 0 | 391 | ok |
| ES.c.0 | 2026 | 97 | 0 | 0 | 391 | ok |
| NQ.c.0 | 2018 | 173 | 3 | 1 | 391 | ok |
| NQ.c.0 | 2019 | 255 | 1 | 0 | 391 | ok |
| NQ.c.0 | 2020 | 256 | 3 | 1 | 391 | ok |
| NQ.c.0 | 2021 | 255 | 1 | 0 | 391 | ok |
| NQ.c.0 | 2022 | 255 | 1 | 0 | 391 | ok |
| NQ.c.0 | 2023 | 254 | 1 | 0 | 391 | ok |
| NQ.c.0 | 2024 | 256 | 1 | 0 | 391 | ok |
| NQ.c.0 | 2025 | 255 | 2 | 0 | 391 | ok |
| NQ.c.0 | 2026 | 98 | 0 | 0 | 391 | ok |
| YM.c.0 | 2018 | 172 | 2 | 0 | 391 | ok |
| YM.c.0 | 2019 | 255 | 1 | 1 | 391 | ok |
| YM.c.0 | 2020 | 255 | 2 | 2 | 391 | ok |
| YM.c.0 | 2021 | 255 | 1 | 1 | 391 | ok |
| YM.c.0 | 2022 | 255 | 1 | 1 | 391 | ok |
| YM.c.0 | 2023 | 254 | 1 | 1 | 391 | ok |
| YM.c.0 | 2024 | 256 | 2 | 1 | 391 | ok |
| YM.c.0 | 2025 | 255 | 3 | 1 | 391 | ok |
| YM.c.0 | 2026 | 97 | 0 | 0 | 391 | ok |
| RTY.c.0 | 2018 | 172 | 2 | 1 | 391 | ok |
| RTY.c.0 | 2019 | 255 | 1 | 1 | 391 | ok |
| RTY.c.0 | 2020 | 256 | 3 | 2 | 391 | ok |
| RTY.c.0 | 2021 | 255 | 1 | 1 | 391 | ok |
| RTY.c.0 | 2022 | 255 | 1 | 1 | 391 | ok |
| RTY.c.0 | 2023 | 254 | 1 | 0 | 391 | ok |
| RTY.c.0 | 2024 | 256 | 2 | 1 | 391 | ok |
| RTY.c.0 | 2025 | 255 | 3 | 1 | 391 | ok |
| RTY.c.0 | 2026 | 97 | 0 | 0 | 391 | ok |

**Severely incomplete days (<50 RTH bars), first 30 of 21:**

| symbol | date | rth_bars |
|---|---|---|
| ES.c.0 | 2018-06-15 | 1 |
| ES.c.0 | 2020-06-30 | 41 |
| ES.c.0 | 2023-06-16 | 1 |
| NQ.c.0 | 2018-06-15 | 1 |
| NQ.c.0 | 2020-06-30 | 41 |
| YM.c.0 | 2019-12-20 | 46 |
| YM.c.0 | 2020-06-30 | 41 |
| YM.c.0 | 2020-12-18 | 32 |
| YM.c.0 | 2021-12-17 | 47 |
| YM.c.0 | 2022-12-16 | 44 |
| YM.c.0 | 2023-12-15 | 45 |
| YM.c.0 | 2024-12-20 | 34 |
| YM.c.0 | 2025-12-19 | 23 |
| RTY.c.0 | 2018-12-21 | 11 |
| RTY.c.0 | 2019-12-20 | 31 |
| RTY.c.0 | 2020-06-30 | 41 |
| RTY.c.0 | 2020-12-18 | 27 |
| RTY.c.0 | 2021-12-17 | 26 |
| RTY.c.0 | 2022-12-16 | 10 |
| RTY.c.0 | 2024-12-20 | 45 |
| RTY.c.0 | 2025-12-19 | 40 |

---

## 2. Tick size + slippage calibration

**Status:** auto-resolved

**Summary:** Per-symbol (high - low) distribution in price points and ticks. Median tick range tells you typical 1m bar volatility. p95 tells you tail volatility. If median is < 2 ticks or > 100 ticks, tick_size config is likely wrong.

**Per-symbol (high - low) distribution:**

| symbol | tick_size | n_bars | hl_p50 (pts) | hl_p95 (pts) | hl_p50 (ticks) | hl_p95 (ticks) |
|---|---|---|---|---|---|---|
| ES.c.0 | 0.25 | 8,872 | 1.750 | 6.250 | 7.0 | 25.0 |
| NQ.c.0 | 0.25 | 8,872 | 7.750 | 29.000 | 31.0 | 116.0 |
| YM.c.0 | 1.0 | 8,872 | 13.000 | 44.000 | 13.0 | 44.0 |
| RTY.c.0 | 0.1 | 8,872 | 1.100 | 4.000 | 11.0 | 40.0 |

---

## 3. Cross-symbol time alignment

**Status:** auto-resolved

**Summary:** Fraction of RTH minutes where all 4 symbols (ES/NQ/YM/RTY) have a bar. Should be >99% in normal regimes. Lower = forward-fill needed or row drops.

**Per-month cross-symbol alignment (% of RTH minutes with all 4 symbols):**

| year | month | total RTH minutes | all 4 present | alignment % |
|---|---|---|---|---|
| 2018 | 06 | 7,821 | 7,778 | 99.45% |
| 2019 | 06 | 7,429 | 7,399 | 99.60% |
| 2020 | 06 | 7,861 | 7,854 | 99.91% |
| 2021 | 06 | 8,211 | 8,199 | 99.85% |
| 2022 | 06 | 8,030 | 8,029 | 99.99% |
| 2023 | 06 | 8,031 | 8,029 | 99.98% |
| 2024 | 06 | 7,248 | 7,103 | 98.00% |
| 2025 | 06 | 7,639 | 7,461 | 97.67% |
| 2026 | 06 | — | — | missing_symbol |

---

## 4. Class balance at k×σ thresholding

**Status:** auto-resolved

**Summary:** With k=0.5, the up/down/flat fractions should each be 25-40% for the model to learn well. Heavy flat (>60%) means k is too high for that horizon. Heavy directional (<10% flat) means k is too low.

**Class balance with k = 0.5:**

| symbol | horizon (min) | n | flat | up | down |
|---|---|---|---|---|---|
| ES.c.0 | 15 | 55,796 | 11.16% | 45.94% | 42.90% |
| ES.c.0 | 30 | 55,796 | 7.79% | 48.37% | 43.84% |
| ES.c.0 | 60 | 55,796 | 5.41% | 50.26% | 44.33% |
| ES.c.0 | 90 | 55,796 | 4.90% | 50.63% | 44.47% |
| ES.c.0 | 240 | 55,161 | 3.30% | 52.92% | 43.78% |
| NQ.c.0 | 15 | 55,788 | 11.38% | 45.60% | 43.03% |
| NQ.c.0 | 30 | 55,788 | 8.20% | 47.74% | 44.06% |
| NQ.c.0 | 60 | 55,788 | 6.01% | 48.97% | 45.02% |
| NQ.c.0 | 90 | 55,788 | 4.99% | 49.46% | 45.55% |
| NQ.c.0 | 240 | 55,153 | 3.25% | 52.77% | 43.98% |
| YM.c.0 | 15 | 55,706 | 11.02% | 46.00% | 42.98% |
| YM.c.0 | 30 | 55,706 | 7.67% | 48.47% | 43.86% |
| YM.c.0 | 60 | 55,706 | 5.43% | 49.90% | 44.67% |
| YM.c.0 | 90 | 55,706 | 4.97% | 50.61% | 44.42% |
| YM.c.0 | 240 | 55,071 | 3.25% | 52.31% | 44.44% |
| RTY.c.0 | 15 | 55,675 | 10.94% | 45.13% | 43.93% |
| RTY.c.0 | 30 | 55,675 | 7.84% | 47.12% | 45.04% |
| RTY.c.0 | 60 | 55,675 | 5.63% | 48.87% | 45.51% |
| RTY.c.0 | 90 | 55,675 | 5.13% | 48.27% | 46.60% |
| RTY.c.0 | 240 | 55,027 | 3.48% | 49.59% | 46.93% |

---

## 5. Vol regime distribution across folds

**Status:** auto-resolved

**Summary:** σ_60 percentiles per (fold, symbol) in bps (basis points per minute). If one fold has 3x the median vol of another, the model may struggle to generalize between regimes. Look for outlier folds.

**σ_60 (bps per minute) percentiles per (fold, symbol):**

| fold | symbol | n | σ p10 (bps) | σ p50 (bps) | σ p90 (bps) | σ p99 (bps) |
|---|---|---|---|---|---|---|
| 1 | ES.c.0 | 24,511 | 1.30 | 2.37 | 5.49 | 10.38 |
| 1 | NQ.c.0 | 24,511 | 1.92 | 3.85 | 8.42 | 14.60 |
| 1 | YM.c.0 | 24,510 | 1.27 | 2.27 | 4.61 | 8.65 |
| 1 | RTY.c.0 | 24,496 | 3.02 | 5.25 | 10.02 | 18.91 |
| 2 | ES.c.0 | 25,234 | 0.99 | 1.63 | 3.20 | 5.59 |
| 2 | NQ.c.0 | 25,234 | 1.36 | 2.46 | 4.73 | 7.43 |
| 2 | YM.c.0 | 25,230 | 1.02 | 1.80 | 3.58 | 5.87 |
| 2 | RTY.c.0 | 25,218 | 2.26 | 3.87 | 7.30 | 10.59 |
| 3 | ES.c.0 | 57,068 | 1.63 | 3.46 | 6.88 | 10.99 |
| 3 | NQ.c.0 | 57,059 | 2.19 | 4.99 | 9.46 | 14.95 |
| 3 | YM.c.0 | 57,015 | 1.54 | 3.14 | 6.18 | 9.69 |
| 3 | RTY.c.0 | 56,994 | 2.88 | 5.31 | 9.77 | 14.87 |
| 4 | ES.c.0 | 89,369 | 2.32 | 4.07 | 7.28 | 13.14 |
| 4 | NQ.c.0 | 89,367 | 3.03 | 5.32 | 9.47 | 16.87 |
| 4 | YM.c.0 | 89,351 | 2.06 | 3.61 | 6.40 | 11.24 |
| 4 | RTY.c.0 | 89,304 | 2.95 | 5.23 | 9.37 | 15.71 |
| 5 | ES.c.0 | 155,289 | 1.39 | 2.39 | 4.15 | 6.82 |
| 5 | NQ.c.0 | 155,291 | 1.95 | 3.44 | 5.83 | 9.44 |
| 5 | YM.c.0 | 155,197 | 1.39 | 2.34 | 4.01 | 6.15 |
| 5 | RTY.c.0 | 155,067 | 2.34 | 4.03 | 7.62 | 12.56 |
| 6 | ES.c.0 | 105,215 | 1.30 | 2.63 | 5.74 | 14.65 |
| 6 | NQ.c.0 | 105,207 | 1.64 | 3.52 | 7.49 | 16.51 |
| 6 | YM.c.0 | 104,951 | 1.51 | 2.80 | 5.38 | 13.13 |
| 6 | RTY.c.0 | 105,027 | 2.28 | 4.26 | 8.22 | 18.30 |

---

## Decisions for build_dataset.py

Based on this audit, populate the following in subsequent commits:

1. **Bad-day exclusion list** (audit 1): exclude any (symbol, date) with < 200 RTH bars from anchor sampling, OR forward-fill, OR drop the symbol's row only.
2. **Slippage config** (audit 2): if hl_ticks_p50 is < 4 or > 40 for any symbol, recheck tick_size. Otherwise default to 1-tick slippage per side.
3. **Cross-symbol alignment rule** (audit 3): if alignment is < 99%, decide between (a) drop misaligned anchor rows, (b) forward-fill the laggard symbol's last bar.
4. **Per-horizon k tuning** (audit 4): if a horizon shows < 15% in any direction at k=0.5, consider lowering k for that horizon.
5. **Vol-stratified evaluation** (audit 5): when reporting fold metrics, also report broken down by σ regime (low/med/high) — folds with very different vol are not directly comparable.
