# Portfolio deep-dive — consensus precision + sweep per-symbol

_Generated 2026-05-15 late evening. Two quick analyses on the 5-signal portfolio assembled after 247 shipped the strict_sweep release._

## TL;DR

1. **Sweep is symbol-agnostic.** Per-symbol breakdown of `sweep_failed_recovered` shows nearly identical precision across NQ/ES/YM (76%/75%/80% mean top-10%). **YM is actually the best** on this signal — opposite of the gap-rejection pattern where YM was weakest. Sweep can deploy across all three contracts with similar weighting.
2. **Naive consensus doesn't help precision.** When 2 signals fire on the same date+symbol, average precision is 0.806 — basically identical to single-signal precision (0.818). So "trade only when 2+ families agree" doesn't add edge over single-signal picks.
3. **3+ signal consensus is genuinely cleaner** (precision 0.944) but rare — only 6 such combos in 2025. Useful as a "high-conviction filter," not as a primary trade trigger.
4. **`sweep_succeeded_held_rejection` is fragile solo.** When it fires without any other signal, precision drops to 37%. It needs companions to be reliable. Drop from solo trading or treat as a "secondary confirmation" only.

## Sweep per-symbol breakdown

`label.strict.next_60m.sweep_failed_recovered`, side=all, 6-year walk-forward 2020-2025:

| Symbol | Mean top-10 prec | Min year | Mean edge | Min edge | 6yr trades |
|---|---:|---:|---:|---:|---:|
| ES.c.0 | 0.765 | 0.694 | +0.525 | +0.447 | 960 |
| NQ.c.0 | 0.751 | 0.681 | +0.515 | +0.465 | 954 |
| **YM.c.0** | **0.799** | **0.748** | **+0.549** | **+0.488** | 957 |
| pooled | 0.775 | 0.713 | +0.533 | +0.482 | 2,872 |

Compare to `resistance_rejection_3bar` (which we ran the same analysis on):

| Symbol | resistance_rejection mean | sweep_failed_recovered mean | Delta |
|---|---:|---:|---:|
| ES.c.0 | 1.000 | 0.765 | gap-rejection is far better on ES |
| NQ.c.0 | 0.934 | 0.751 | gap-rejection edge on NQ |
| YM.c.0 | 0.892 | 0.799 | sweep ties on YM |

**Important nuance:** the two signals don't compete — they fire on **different events** (gap-rejection at 09:30 ET on gap days only; sweep whenever a level gets swept intraday). The per-symbol comparison is just to understand which contract is the "best home" for each signal.

**Deployment implication:** if/when we translate sweep into a real strategy, we'd run it on all three contracts equally. If/when we translate gap-rejection, ES gets the largest allocation, YM gets the smallest (or zero).

Visual: [top10_precision_by_symbol_year.png](../experiments/backtests/2026-05-15_sweep_per_symbol/top10_precision_by_symbol_year.png).

## Consensus precision

In test_year=2025, the 5 active signals collectively produced **879 raw top-10% picks** across **380 unique date×symbol combinations**. Distribution of consensus tiers:

| # signals firing on same date+symbol | Unique combos | Underlying trades | Hits | Avg precision |
|---:|---:|---:|---:|---:|
| 1 (solo) | 214 | 214 | 175 | **0.818** |
| 2 (pair consensus) | 160 | 320 | 258 | 0.806 |
| 3+ | 6 | 18 | 17 | **0.944** |

**Reading:** 2-signal consensus is **statistically indistinguishable** from solo (0.806 vs 0.818) in this single test year. 3-signal consensus is meaningfully better but the sample (6 combos, 18 trades) is too small to be confident.

So **no simple "consensus filter" knob** for v1. Single-signal picks are the right unit.

### Pair-wise consensus precision (clean 2-signal combos only)

When exactly two specific signals fire on the same date+symbol (and no others):

| Signal A | Signal B | n combos | trades | hits | precision |
|---|---|---:|---:|---:|---:|
| sweep_failed_recovered | sweep_succeeded_held_rejection | 126 | 252 | 193 | 0.766 |
| ogap_gap_up_rejection | ogap_strict_partial_touch | 15 | 30 | 30 | **1.000** |
| ogap_gap_down_rejection | ogap_strict_partial_touch | 13 | 26 | 24 | 0.923 |
| smt_pd_high_thesis | sweep_failed_recovered | 5 | 10 | 9 | 0.900 |
| ogap_gap_down_rejection | sweep_failed_recovered | 1 | 2 | 2 | 1.000 |

**Reading:** The cleanest pair consensus is **within-OGAP-family** (gap_up + strict partial = 100% on 15 combos; gap_down + strict partial = 92% on 13 combos). The cross-family pair (SMT + sweep) on 5 combos is too small to interpret.

### Solo-signal precision (when each fires WITHOUT any other signal)

| Signal | n solo combos | n trades | hits | solo precision |
|---|---:|---:|---:|---:|
| ogap_gap_down_rejection | 7 | 7 | 7 | **1.000** |
| ogap_gap_up_rejection | 7 | 7 | 7 | **1.000** |
| smt_pd_high_thesis | 3 | 3 | 3 | **1.000** |
| sweep_failed_recovered | 156 | 156 | 136 | 0.872 |
| ogap_strict_partial_touch | 14 | 14 | 12 | 0.857 |
| **sweep_succeeded_held_rejection** | **27** | **27** | **10** | **0.370** |

**Critical finding:** `sweep_succeeded_held_rejection` solo precision is **0.37** — barely better than coin flip and well below the signal's overall 60% top-10% precision. When it fires *with* `sweep_failed_recovered` (the in-family pair), pair precision is 0.77. So this signal needs a companion.

**Recommended action:** treat `sweep_succeeded_held_rejection` as a **secondary signal** that requires confirmation by `sweep_failed_recovered` (or another signal) before trading.

## What this changes about the next moves

1. **Drop `sweep_succeeded_held_rejection` from solo trading.** The signal works only when corroborated. Either remove from the trade list, or only trigger when 2+ signals agree.
2. **No consensus filter for v1.** Simple "fire when 2+ signals agree" doesn't add precision over single-signal — and would cut trade count in half. Keep single-signal picks as the unit.
3. **Sweep deploys across all 3 symbols.** YM is slightly the best on this signal (the opposite of gap-rejection's pattern). Equal weighting across NQ/ES/YM is defensible.
4. **The 3+ signal consensus tier (precision 0.944) is intriguing** but the 2025 sample is 6 combos. Worth re-checking in multi-year analysis.

## Caveats / things to verify

- The "no consensus boost" finding is based on **one test year**. Need to repeat across 2020-2024 to confirm.
- `sweep_succeeded_held_rejection` and `sweep_failed_recovered` are **labeling different outcomes of the same sweep event** — they can co-occur on the same anchor row if the model is uncertain about direction. The pair precision of 0.77 means "when both fire, 77% of the underlying labels are 1" — but they're predicting different things, so this isn't quite traditional consensus. Worth understanding the semantics better with 247.
- Solo-signal samples for SMT (3), ogap_gap_up (7), and ogap_gap_down (7) are too small to be statistically confident at 100% precision. The 6-year multi-test-year version would have larger samples.

## Reproducing

```bash
# Sweep per-symbol breakdown (5 min):
python -m scripts.ml.sweep_per_symbol

# Consensus precision check (instant — reads existing predictions):
python -m scripts.ml.consensus_precision_check
```

Outputs under `experiments/backtests/2026-05-15_sweep_per_symbol/` and `experiments/backtests/2026-05-15_consensus_precision/`.
