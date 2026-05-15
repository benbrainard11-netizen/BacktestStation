# Label tournament — multi-year robustness ranking

_Generated 2026-05-15. Ten candidate labels from the top of the registry, each evaluated with the same six-test-year walk-forward backtest as the resistance_rejection winner. Run time: 3.1 minutes on RTX 5080._

## TL;DR — six robust signals, not one

The lab has more edge than the single `resistance_rejection_3bar` result suggested. Of the ten top-registry labels tested:

- **6 ROBUST** (top-10% precision ≥ 0.85 in ≥ 5 of 6 years)
- **2 MIXED** (passes in 3-4 of 6 years)
- **2 FLUKE** (passes in 0-1 of 6 years)

The strongest single signal — by a wide margin — is **SMT period-close `n1_thesis_confirmed_strict`** on `side=high`. It hit 100% top-10% precision in every single test year. Mean edge over base rate: **+59 percentage points**.

## Full ranking

Sorted by mean top-10% precision across 6 test years (2020-2025).

| Rank | Candidate | Mean AUC | Mean base | **Mean top-10% prec** | Min top-10% | Mean edge | Min edge | 6yr signals | Verdict |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | smt_previous_day / high / `n1_thesis_confirmed_strict` | 0.961 | 0.409 | **1.000** | 1.000 | +0.591 | +0.547 | 69 | ROBUST 6/6 |
| 2 | smt_previous_day / high / `n1_primary_took_period_n_low` | 0.961 | 0.409 | **1.000** | 1.000 | +0.591 | +0.547 | 69 | ROBUST 6/6 |
| 3 | smt_previous_day / high / `n1_close_moved_with_thesis` | 0.969 | 0.409 | **0.986** | 0.917 | +0.577 | +0.485 | 69 | ROBUST 6/6 |
| 4 | opening_gap_broad / gap_down / `resistance_rejection_3bar` ⭐ original winner | 0.749 | 0.644 | **0.950** | 0.794 | +0.305 | +0.209 | 231 | ROBUST 5/6 |
| 5 | opening_gap_broad / gap_up / `support_rejection_3bar` ⭐ mirror | 0.723 | 0.656 | **0.937** | 0.833 | +0.281 | +0.207 | 286 | ROBUST 5/6 |
| 6 | opening_gap_strict / all / `strict.next_60m.partial_touch_rejected` | 0.831 | 0.329 | **0.881** | 0.807 | +0.552 | +0.514 | 515 | ROBUST 5/6 |
| 7 | opening_gap_broad / all / `next_60m.unfilled_at_window_end` | 0.830 | 0.329 | 0.872 | 0.831 | +0.543 | +0.469 | 515 | MIXED 4/6 |
| 8 | opening_gap_strict / gap_down / `strict.next_60m.partial_touch_rejected` | 0.829 | 0.315 | 0.855 | 0.698 | +0.540 | +0.396 | 231 | MIXED 3/6 |
| 9 | forming_vp / all / `next_60m.took_profile_so_far_high` | 0.888 | 0.240 | 0.791 | 0.754 | +0.551 | +0.519 | 2,291 | FLUKE 1/6 |
| 10 | forming_vp / all / `next_60m.took_profile_so_far_low` | 0.877 | 0.194 | 0.729 | 0.689 | +0.535 | +0.503 | 2,291 | FLUKE 0/6 |

## Notable observations

### SMT period-close is the strongest signal we have

Three SMT period-close labels all show **100% top-10% precision in every year** (or 98.6% in the case of `n1_close_moved_with_thesis`). Mean edge over base rate is +0.58 — almost twice the edge we measured on `resistance_rejection_3bar`. 69 trades over 6 years = ~11 trades per year — a premium-quality, low-frequency setup.

**Caveat**: the three SMT labels have **identical** 100% precision and 69-signal counts. They're either measuring the same underlying market behavior with different labeling lenses, or they're tautologically related (a "thesis confirmed strict" event might definitionally imply "primary took period_n low" on a high-side SMT). Worth checking with 247 before treating these as three independent signals.

### Bidirectional gap-rejection works

The original winner (`resistance_rejection_3bar` on `gap_down`) and its mirror (`support_rejection_3bar` on `gap_up`) both pass ROBUST. Combined, they cover **both gap directions on every trading day**. That gives you a strategy with ~85-95 trades per year (top-10% across both sides) instead of ~40 from the single winner alone.

### Opening_gap strict labels add a third dimension

`strict.next_60m.partial_touch_rejected` at `side=all` is the highest-volume robust signal (515 trades over 6 years, ~85/year). The strict-label structure (with a 33% base rate instead of 64%) makes it a different *shape* of signal — lower precision (88% mean) but much larger lift over base rate (+0.55 edge). Could be a complement to the gap-rejection labels rather than a replacement.

### forming_vp labels are noisier than they look

Both forming_vp labels have great AUC (0.88) and lift (+0.50+), but they FAIL the top-10% precision robustness bar because the base rates are so low (0.19-0.24) that top-10% precision varies a lot year-to-year. They might still be tradeable with a different decision rule (e.g., score > 0.5 instead of "top 10% of distribution"), but the absolute precision bar we used for verdicts doesn't fit them. **Don't dismiss these without trying the alternative decision rule first.**

## What this means for the project

**Before tournament:** the lab had one signal that survived walk-forward.

**After tournament:** the lab has a **portfolio of signals**, with the strongest one (`n1_thesis_confirmed_strict` on SMT period-close) clearly dominating the original gap_down winner.

The natural strategic next moves shift:

1. **SMT period-close is now the headline signal to translate into a real strategy**, not `resistance_rejection_3bar`. Same v2 walk-forward template, but applied to a different (and stronger) anchor.
2. **The bidirectional gap-rejection pair is the secondary play.** Combined ~85 trades/year, robust on both sides.
3. **The strict opening_gap label** (`partial_touch_rejected@60m`) is a high-volume third option.
4. **Multi-signal portfolio is possible.** With six robust signals, the lab could combine them — capital-allocate by edge and signal frequency.

## Per-symbol breakdown (only done for the original winner — TODO for others)

Per-symbol analysis of `resistance_rejection_3bar` ([v3 doc](../experiments/backtests/2026-05-15_resistance_rejection_v3_per_symbol/verdict.json)) showed **ES.c.0 is the workhorse** (100% top-10% precision in every year), with NQ second and YM trailing. Worth repeating this split on the SMT signals to see if they have similar per-symbol concentration before trade-direction decisions.

## Things still missing (same as v2)

- Real P&L (OHLCV-driven backtest with entry/stop/target rules)
- Transaction costs
- Per-symbol breakdown for the SMT signals
- Diagnostic for why `forming_vp` signals fail the top-10% precision bar despite high AUC

## Reproducing

```bash
python -m scripts.ml.label_tournament_2026_05_15
```

Outputs in `experiments/backtests/2026-05-15_label_tournament/`:

- `per_candidate_per_year.csv` — one row per (candidate × test_year × top_pct=0.10)
- `candidate_ranking.csv` — aggregated ranking with verdict
- `candidate_ranking.png` — horizontal bar chart with verdict color-coding
- `summary.json` — high-level counts + runtime

10 candidates × 6 test years × single fold ≈ 3 minutes on RTX 5080.
