# Strict sweep labels — GPU walk-forward + portfolio addition

_Generated 2026-05-15 evening. Follow-up to 247's `strategy-lab-core-2026-05-15-strict-sweep` release. Two findings: (1) the sweep family is the 5th independent signal family, and (2) the absolute-precision verdict bar I used yesterday was mis-calibrated for low-base-rate labels — the corrected verdict expands the lab's robust-signal count meaningfully._

## TL;DR

1. **`sweep_failed_recovered` is the highest-volume robust signal in the lab.** ~476 top-10% picks per year (10× the gap_down rejection signal), 77-83% precision, edge +0.53 over base rate. Min-year edge +0.48 — stable across 6 years.
2. **Sweep is genuinely independent from SMT and OGAP.** Jaccard overlap with all 4 yesterday-robust signals is **0.00 - 0.03**. Adds a fifth independent family to the portfolio.
3. **Verdict framework correction needed.** The "0.85 absolute precision" bar from yesterday under-counts robust signals when base rates are low. By the cleaner *edge-over-base-rate* bar (min-year edge ≥ +0.20), `sweep_failed_recovered`, the `forming_vp` labels we previously called FLUKE, and likely several others are actually robust.

## What 247 shipped

Release: [`strategy-lab-core-2026-05-15-strict-sweep`](https://github.com/benbrainard11-netizen/BacktestStation/releases/tag/strategy-lab-core-2026-05-15-strict-sweep) (commit `8cd2373`).

- New matrix: `sweep_snapshots_xctx_fvggeom_obgeom_liqgeom_regime_strict.parquet` (52,946 rows × 3,248 cols).
- 10 new strict labels across two horizons (`next_60m`, `next_240m`) × 5 behavioral concepts:
  - `sweep_failed_recovered` (price closed back through swept level + rejected)
  - `sweep_succeeded_held_rejection` (level held + sharp rejection)
  - `sweep_partial_retest_rejected`
  - `sweep_failed_immediately`
  - `sweep_extended_continuation`

## GPU walk-forward results (12 configs × 6 years)

Top by mean top-10% precision:

| Config | Mean AUC | Mean base | Mean top-10% prec | Min year | Mean edge | Min edge |
|---|---:|---:|---:|---:|---:|---:|
| `sweep_failed_recovered@60m` / low | 0.908 | 0.271 | **0.827** | 0.744 | **+0.556** | +0.518 |
| `sweep_failed_recovered@60m` / all | 0.902 | 0.242 | 0.775 | 0.713 | +0.533 | +0.482 |
| `sweep_failed_recovered@60m` / high | 0.909 | 0.219 | 0.774 | 0.714 | +0.555 | +0.491 |
| `sweep_failed_recovered@240m` / all | 0.856 | 0.256 | 0.680 | 0.605 | +0.424 | +0.368 |
| `sweep_succeeded_held_rejection@60m` / all | 0.892 | 0.144 | 0.523 | 0.495 | +0.380 | +0.360 |
| `sweep_succeeded_held_rejection@240m` / all | 0.824 | 0.172 | 0.455 | 0.415 | +0.283 | +0.245 |
| `sweep_failed_immediately@240m` / all | 0.730 | 0.198 | 0.446 | 0.397 | +0.248 | +0.202 |
| `sweep_failed_immediately@60m` / all | 0.728 | 0.198 | 0.444 | 0.395 | +0.246 | +0.199 |
| `sweep_extended_continuation@240m` / all | 0.722 | 0.112 | 0.272 | 0.197 | +0.160 | +0.079 |
| `sweep_partial_retest_rejected@240m` / all | 0.759 | 0.091 | 0.214 | 0.194 | +0.123 | +0.103 |
| `sweep_extended_continuation@60m` / all | 0.798 | 0.065 | 0.208 | 0.168 | +0.143 | +0.103 |
| `sweep_partial_retest_rejected@60m` / all | 0.827 | 0.058 | 0.190 | 0.127 | +0.132 | +0.073 |

Note: GPU AUC mean (0.902-0.909 for `sweep_failed_recovered`) matches 247's CPU baseline (0.903-0.910) within +/-0.01. As we've seen across every comparison: GPU ≈ CPU on quality, GPU wins on throughput.

## The verdict framework correction

Yesterday's verdict bar was **"top-10% absolute precision ≥ 0.85 in ≥ 5 of 6 years."** That bar works for labels with base rates of 0.40-0.65 (SMT period-close, gap-rejection). It **does not work** for strict labels with base rates of 0.06-0.27, because the practical precision ceiling is bounded by `base_rate + max_lift`.

Examples:
- `sweep_failed_recovered@60m / low`: base 0.271, top-10% prec 0.827, edge **+0.556**. By absolute bar: FLUKE (2/6). By edge bar: ROBUST.
- `forming_vp / all / took_profile_so_far_high` (from yesterday's tournament): base 0.240, top-10% prec 0.791, edge **+0.551**. By absolute bar: FLUKE (1/6). By edge bar: ROBUST.

**Proposed corrected verdict:**

> **ROBUST_EDGE** = min-year edge over base rate ≥ +0.20 AND mean-year edge ≥ +0.30 AND min-year edge ≥ 50% of mean-year edge (stability).

Under this rule:

| Config | Old verdict | New verdict | Reason |
|---|---|---|---|
| sweep_failed_recovered (low/all/high) | FLUKE | **ROBUST_EDGE** | Mean edge +0.53, min +0.48 |
| sweep_succeeded_held_rejection@60m | FLUKE | **ROBUST_EDGE** | Mean edge +0.38, min +0.36 |
| sweep_failed_immediately@60m | FLUKE | BORDERLINE | Mean +0.25, min +0.20 |
| forming_vp / took_profile_so_far_high | FLUKE | **ROBUST_EDGE** | Mean edge +0.55, min +0.52 |
| forming_vp / took_profile_so_far_low | FLUKE | **ROBUST_EDGE** | Mean edge +0.54, min +0.50 |

So the lab's effective robust-signal count goes from **4** (yesterday's bar) to **~8** (corrected bar), with multiple labels per family.

## Cross-family overlap (with sweep added)

Pairwise Jaccard on top-10% picks in test_year=2025:

| | SMT thesis | OGAP gap_down | OGAP gap_up | OGAP strict | SWEEP failed_rec | SWEEP succeeded |
|---|---:|---:|---:|---:|---:|---:|
| SMT thesis | 1.000 | 0.000 | 0.000 | 0.000 | 0.030 | 0.024 |
| OGAP gap_down | 0.000 | 1.000 | 0.000 | 0.288 | 0.010 | 0.000 |
| OGAP gap_up | 0.000 | 0.000 | 1.000 | 0.294 | 0.000 | 0.000 |
| OGAP strict | 0.000 | 0.288 | 0.294 | 1.000 | 0.006 | 0.000 |
| **SWEEP failed_rec** | **0.030** | **0.010** | **0.000** | **0.006** | 1.000 | 0.405 |
| **SWEEP succeeded** | 0.024 | 0.000 | 0.000 | 0.000 | 0.405 | 1.000 |

Sweep family is **completely independent** from SMT and OGAP. Adds genuine portfolio diversification.

Visual: [overlap_heatmap.png](../experiments/backtests/2026-05-15_portfolio_with_sweep/overlap_heatmap.png).

## Portfolio in 2025 (with sweep)

- **879 raw top-10% picks** across all 5 families combined
- **380 unique date×symbol trading opportunities** (up from 75 without sweep)
- 214 single-signal picks (56%)
- 160 two-signal consensus pairs (42%)
- 6 three-signal consensus combos (2%)

Sweep dominates the trade-count: ~476 sweep picks alone vs ~218 from all the OGAP+SMT signals combined. If we're capacity-limited, sweep is where the volume is.

## What the 5 robust signal families look like together

| Family | Headline label | Trade freq (per yr) | Precision | Edge | Symbols |
|---|---|---:|---:|---:|---|
| SMT period_close | `n1_thesis_confirmed_strict` (high) | ~12 | 100% | +0.59 | all 3 (NQ/ES/YM) |
| OGAP gap_down rej | `next_60m.resistance_rejection_3bar` | ~43 | 95% | +0.30 | ES-dominant |
| OGAP gap_up rej | `next_60m.support_rejection_3bar` | ~44 | 94% | +0.28 | TBD |
| OGAP strict partial | `strict.next_60m.partial_touch_rejected` | ~87 | 88% | +0.55 | TBD |
| SWEEP failed_rec | `strict.next_60m.sweep_failed_recovered` | ~476 | 78-83% | +0.53 | TBD |

Combined ~660 picks per year per index symbol, ~2.5 per trading day. Across 3 symbols if all generalize: ~8 trades/day.

## What this changes about the next moves

The Strategy v1 draft ([STRATEGY_V1_DRAFT_2026_05_15.md](STRATEGY_V1_DRAFT_2026_05_15.md)) is still the right design surface, but the signal list grows from 4 to 5:

1. Add **`sweep_failed_recovered`** as the high-volume primary signal alongside SMT period_close.
2. Re-examine **`forming_vp.took_profile_so_far_high/low`** under the corrected edge bar — they were misclassified in yesterday's tournament.
3. **Decide on the verdict framework** before re-running the tournament. Edge-based vs precision-based produces different shortlists. Edge-based is the more honest metric.

Per-symbol breakdown of `sweep_failed_recovered` is the obvious next quick check — does it generalize across ES/NQ/YM like SMT, or concentrate on one contract like `resistance_rejection_3bar`? Same v3 framework, ~5 min.

## Reproducing

```bash
# Walk-forward across the 12 sweep configs:
python -m scripts.ml.sweep_strict_walkforward_2026_05_15

# Cross-family overlap including sweep:
python -m scripts.ml.portfolio_with_sweep_2026_05_15
```

Outputs:
- `experiments/backtests/2026-05-15_strict_sweep_walkforward/` — per-label-per-year, ranking, plot
- `experiments/backtests/2026-05-15_portfolio_with_sweep/` — overlap pivot, heatmap, summary
