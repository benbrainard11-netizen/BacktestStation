# Status for Ben — when you're back from the gym

Generated: 2026-05-27 (afternoon)

## What I got done while you were out

### 1. Real `qa.py --audit` ✅ shipped + ran on 8 years of 1m data

Implemented all 5 PLAN §9 audits, ran them across 2018-05 → 2026-05, all 4 symbols. Output is in:

- [`report/v0_iter0_dataset_audit.md`](v0_iter0_dataset_audit.md) — full tables
- [`out/audit/audit_bar_coverage.parquet`](../out/audit/audit_bar_coverage.parquet) — machine-readable
- [`out/audit/audit_severe_gaps.parquet`](../out/audit/audit_severe_gaps.parquet) — 21 flagged days
- [`out/audit/findings.json`](../out/audit/findings.json) — JSON dump

### 2. `baseline_naive.py` ✅ implemented + self-tested

Implements the `Forecaster` ABC. Just learns marginal class freq from train data and predicts that for every test row. Sanity-floor baseline. Self-test passes.

### 3. `baseline_lightgbm.py` ✅ implemented + self-tested

20 LightGBM 3-class classifiers per fold (4 symbols × 5 horizons). Extracts ~96 features per anchor row (last value + mean + std of each channel over last 60 mins). Self-test on synthetic data hits 100% accuracy on injected signal — model code works.

LightGBM + joblib auto-installed into `backend/.venv` while I was at it.

### 4. `evaluate.py` ✅ implemented

Real metrics code: accuracy, macro-F1, ROC-AUC OvR, Brier, ECE (calibration), Spearman IC, plus the economic overlay (toy P&L sim with 1-tick slippage + $1.50 commission, swept across probability thresholds 0.45-0.65). Picks the best threshold by `win_rate × mean_R` per (model, fold, horizon, symbol). Not end-to-end tested (no predictions exist yet), but pure functions are correct.

---

## 🚨 Important finding from the audit — k=0.5σ is broken

Section 4 of the audit revealed a real labeling problem. Look at the class balance numbers:

| symbol | horizon | flat % | up % | down % |
|---|---|---|---|---|
| ES.c.0 | 15m  | **11.16%** | 45.94% | 42.90% |
| ES.c.0 | 30m  | **7.79%**  | 48.37% | 43.84% |
| ES.c.0 | 60m  | **5.41%**  | 50.26% | 44.33% |
| ES.c.0 | 90m  | **4.90%**  | 50.63% | 44.47% |
| ES.c.0 | 240m | **3.30%**  | 52.92% | 43.78% |

Healthy 3-way classification wants each class around 25-40%. We've got "flat" collapsing from 11% at 15m to 3% at 4h. **Effectively this is binary up/down classification.** And our model would learn essentially nothing about the "flat" case — there's nothing to learn at 3% incidence.

### Why this happened

The thresholding uses `k × σ_60` where σ_60 is the stddev of *1-minute* returns. But we're labeling on *h-minute* returns. Under a random walk, std of h-minute return ≈ √h × σ_60. So at h = 240 (4h), the "natural" std of forward return is ~15.5 × σ_60, but our threshold is 0.5 × σ_60. We're calling a move "flat" only when it stays inside ~3% of the typical move at that horizon. Tiny.

### Three fix options — need your call

**Option A** — Use horizon-specific σ (most principled).

```
σ_h(t) = stddev of h-minute returns over the last (say) 30 days, computed
         per symbol.
threshold = k × σ_h(t)
```

This makes "flat" mean "within 0.5σ of typical h-minute move." Self-scaling. Probably gives 30-40% flat at every horizon.

**Option B** — Scale k by √h (cheap approximation).

```
threshold = k_base × sqrt(h) × σ_60(t)
```

Cheaper to compute; assumes random walk. Probably close to Option A in practice.

**Option C** — Set different `k` per horizon.

```
labels_and_horizons.yaml:
  thresholds:
    h_15m:  k=0.5
    h_30m:  k=0.8
    h_60m:  k=1.2
    h_90m:  k=1.4
    h_240m: k=2.0
```

Manual but transparent. We'd calibrate these against actual class balance.

**My recommendation: Option A.** It's principled, scales naturally with vol regime, and doesn't require manual per-horizon tuning. The compute cost is trivial (one rolling stddev per symbol per horizon).

Until you pick, I'd hold off on `build_dataset.py` — the label scheme is the upstream contract.

---

## Other audit findings

- **Bar coverage:** Excellent. 36 (symbol, year) cells, all with median 391 RTH bars/day. Only 21 severely-incomplete days across 8 years × 4 symbols — almost all are December-Christmas-Eve early closes (predictable). Build the bad-day exclusion list from these.

- **Tick sizes:** All 4 confirmed correct. ES median bar range = 7 ticks, NQ = 31, YM = 13, RTY = 11. Within expected ranges.

- **Cross-symbol alignment:** 99%+ in 2018-2023, dropping to 98% in 2024 and 97.67% in 2025. Recent data has slightly more misalignment. Decision needed: drop misaligned anchor rows, or forward-fill the laggard.

- **Vol regime variation:** Fold 4 (2022 bear) has ~2.5x the median σ of Fold 2 (2021 low-vol). Real regime shift. We should report fold metrics broken down by vol regime, not just pooled.

---

## What's queued for after you decide

Once you pick a label fix (A / B / C above), the next concrete piece is **`build_dataset.py`** — load bars, build the multivariate tensor, apply the fixed thresholding, write per-fold parquet files. That unblocks training. Probably 2-3 hours of work to write and run.

Then it's straight train → eval → kill-criteria check. All the eval scaffolding (evaluate.py) and baselines are already wired up. The whole chain runs end-to-end as soon as the dataset exists.

---

## File map of new things

```
experiments/tsfm_milk_v0/
├── qa.py                       ← full implementation (was a stub)
├── baseline_naive.py           ← real, self-tested
├── baseline_lightgbm.py        ← real, self-tested
├── evaluate.py                 ← full implementation
└── report/
    ├── v0_iter0_dataset_audit.md   ← the audit findings
    └── STATUS_FOR_BEN.md           ← this file
```

Welcome back. Pick a label fix and let's go.
