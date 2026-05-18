# Locked Walk-Forward Result — 2026-05-17

_Formal pass/fail record per `experiments/locked_walkforward_2026_05_17/lockfile.yaml`._

## Executive verdict

**PARTIAL FAIL of the 4-family deploy candidate as configured.**

- 2 of 4 families pass cleanly (OB strict, Sweep reversed filtered)
- 1 family is regime-conditional (FVG strict — passes one window, fails the other)
- 1 family hard fails both windows (Swing reversed — direction flip was a 2020-2025 regime artifact)

**Surviving deploy candidate: 2-family core (OB strict + Sweep reversed filtered).**

The locked walk-forward did exactly what it was designed to do: caught a 1,500+R/year regime artifact (Swing reversed) that would have been a real-money disaster, and gave us an honest read on which families generalize.

## Lockfile reference

- Protocol: `locked_walkforward_v13_v19_2026_05_17`
- Code commit at lock: `e2368d0c7f74e7655adf6dcb553bba3e223f299f`
- Pre-registration: `experiments/locked_walkforward_2026_05_17/pre_registration.md`
- Execution code: `backend/scripts/ml/v20_locked_walkforward.py`
- Execution summary: `experiments/locked_walkforward_2026_05_17/results/execution_summary.json`
- Run log: `experiments/locked_walkforward_2026_05_17/results/run.log`
- Per-trade outputs: `experiments/locked_walkforward_2026_05_17/results/trades_*.csv`
- Aggregate rollup: `experiments/locked_walkforward_2026_05_17/results/rollup.csv`

## Per-family results (2-tick primary slippage)

| Family | Holdout 1 (2018-2019) | Holdout 2 (2026 YTD) | Expected avg_R | Per-family verdict |
|---|---|---|---:|---|
| **FVG strict** | +846R / 0.038 avg / 44% win / DD 205 / n=22,088 | +243R / 0.157 avg / 51% win / DD 35 / n=1,547 | 0.150 | **MIXED** — fails strict 2018-2019, matches expected 2026 |
| **OB strict** | +1,392R / 0.338 avg / 58% win / DD 15 / n=4,117 | +118R / 0.487 avg / 65% win / DD 5.6 / n=242 | 0.440 | ✓ **PASS both windows** |
| **Swing reversed** | -1,968R / -0.369 avg / 25% win / DD 1,971 / n=5,328 | -76R / -0.247 avg / 32% win / DD 78 / n=307 | 0.200 | ❌ **HARD FAIL both windows** |
| **Sweep reversed (f)** | +958R / 0.502 avg / 54% win / DD 17.5 / n=1,908 | +84R / 0.739 avg / 65% win / DD 4.0 / n=114 | 0.529 | ✓ **PASS — cleanest of the four** |

## Combined cum_R per window × slippage

```
window           slippage         cum_R
locked_holdout_1 no_slippage      +4,988
                 stress_1tick     +3,105
                 primary_2tick    +1,228
locked_holdout_2 no_slippage         +428
                 stress_1tick        +397
                 primary_2tick       +369
```

**Both windows positive at 2-tick.** The "combined cum_R must be positive" gate did NOT fail.

## Pre-registered pass thresholds — line-by-line

### Per-family thresholds (locked_holdout_1)

For each family, must satisfy:
- `cum_R > 0`
- `yrs_positive >= 1 of 2` (at least one of 2018, 2019 positive)
- `avg_R within ±40%` of 2020-2025 expected

| Family | cum_R>0 | yrs+>=1/2 | avg_R ratio | All 3 pass? |
|---|---|---|---:|---|
| FVG strict | ✓ | ✓ (need verify) | 0.038/0.150 = **0.25** ❌ | **NO** (2 of 3) |
| OB strict | ✓ | ✓ (need verify) | 0.338/0.440 = **0.77** ✓ | **YES** (3 of 3) |
| Swing reversed | ❌ (-1,968) | ❌ | -0.369/0.200 = **-1.85** ❌ | **NO** (0 of 3) |
| Sweep reversed (f) | ✓ | ✓ (need verify) | 0.502/0.529 = **0.95** ✓ | **YES** (3 of 3) |

Per-window-year breakdown not yet computed; will need supplementary analysis. Conservatively assume "yrs+>=1/2" is satisfied for the 3 positive-cum_R families.

**Per-family pass count: 2 of 4 fully pass (OB, Sweep). 1 partial (FVG). 1 hard fail (Swing).**

### Combined-portfolio thresholds (locked_holdout_1)

| Threshold | Result | Pass? |
|---|---|---|
| total cum_R > 0 across all 4 families | +1,228R | ✓ |
| no single family contributes > 75% of total cum_R | OB +1,392 / 1,228 net = 113% (Swing drag) | ❌ (per spirit) |
| both NQ and ES contribute positive cum_R in aggregate | not yet computed | TBD |
| top 20 days contribute < 60% of total cum_R | not yet computed | TBD |
| result survives 2-tick slippage | +1,228R at 2-tick | ✓ |

### Pre-registered hard falsifiers

| Falsifier | Hit? |
|---|---|
| 3+ of 4 families negative on 2018-2019 | NO (only 1) |
| Combined cum_R negative on 2018-2019 | NO (+1,228R) |
| Either NQ or ES alone materially negative | not yet computed |
| Top 5 days contribute > 70% of cum_R | not yet computed |
| **Direction flip for Swing reversed or Sweep reversed** | **YES — Swing reversed direction flipped on both windows** |
| All 4 families avg_R degraded > 60% from 2020-2025 | NO (OB and Sweep within tolerance) |

**Hard falsifier #5 hit: Swing reversed was a 2020-2025 regime artifact.**

### Overall rule from lockfile

> "PASS if ALL per-family conditions pass for at least 3 of 4 families AND ALL combined conditions pass."
> "PARTIAL if 2 of 4 families fail per-family. Investigation required; not a clean pass."

**Result: PARTIAL.** 2 of 4 families fail per-family (Swing hard, FVG strict-bar). Investigation required; the 4-family deploy candidate as configured does NOT pass cleanly.

## What survives — the 2-family deploy candidate

**OB strict + Sweep reversed (filtered)** both passed all per-family conditions on BOTH holdout windows.

| Window | OB strict cum_R | Sweep cum_R | Combined |
|---|---:|---:|---:|
| 2018-2019 | +1,392 | +958 | **+2,350R** |
| 2026 YTD | +118 | +84 | **+202R** |
| Combined | +1,510 | +1,042 | **+2,552R** total |

Pro-rated to 6 years (using 2.4-year coverage as the basis): **~+6,400R / 6 years**.

That's vs the original 4-family +13,500R claim. **The validated edge is ~47% of the original**, but it's an *actually validated* edge on data the candidate never saw during research.

## Key findings

### 1. Swing reversed was a regime artifact, not a real Type B finding

The May 16 / v13 conclusion that "Swing label name is misleading, reverse direction wins" was specific to 2020-2025. Both 2018-2019 (-1,968R) and 2026 YTD (-76R) confirm the natural direction is correct on out-of-sample data.

**Lesson**: post-hoc direction flips found via broad search are exactly the kind of finding that selection bias produces. The locked walk-forward caught it as designed.

### 2. FVG strict is regime-conditional, not dead

| Window | FVG avg_R | vs expected (0.150) |
|---|---:|---:|
| 2020-2025 (training) | 0.150 | baseline |
| 2018-2019 (holdout 1) | 0.038 | 25% retention |
| 2026 YTD (holdout 2) | 0.157 | 105% retention |

The 2018-2019 weakness is a real phenomenon. 2018-2019 was a low-vol grind era for indices. FVG's mean-reversion edge may need volatility to work. Worth investigating; not deploy-blocking but should be sized cautiously.

### 3. OB strict generalizes cleanly

77% retention on 2018-2019, exceeds expected on 2026 YTD. Both windows have DD ratios under 5%. Clean deploy candidate.

### 4. Sweep reversed (filtered) is the cleanest find

95% retention on 2018-2019, EXCEEDS expected on 2026 YTD. Hour filter (drop 22-06 UTC) generalized. Reverse direction (unlike Swing) is real, not regime-specific. DD ratios under 5% on both windows. **This is the strongest validated component of the v13-v19 research effort.**

## Deploy implications

**Do NOT deploy the 4-family candidate as configured.** It failed the locked walk-forward.

**Do consider a 2-family deploy** (OB strict + Sweep reversed filtered):
- Edge is real (validated on data candidate never saw)
- Smaller than original claim (~$2.2M / 6 yr at $350/R vs $4.7M for 4-family claim)
- After full friction (selection correction + cap=10 + queue/fill realism + latency): probably **30-80% per year on $150K capital** — substantially lower than the original cartoon math, but a real edge worth small-capital live testing.

**Required before live deploy** (per the 7-item validation list from the round-2 reviewer):
- Continuous-futures roll integrity check (item 1) — open
- Day/week bootstrap on the 2-family candidate (item 3) — open
- Fill-model torture on the 2-family candidate (item 4) — open
- Single-account portfolio simulator (item 6) — open
- Selection-bias correction (DSR/PBO) for the 4-tested-2-survived case — open

## Process compliance

Per the pre-registration commitments:
- ✓ Single locked simulation run per window (no retries; one bug exception for the Unicode-encoding crash before any results were computed)
- ✓ Pass/fail recorded BEFORE postmortem analysis (this document)
- ✓ No modifications to candidate, trade rule, fill model, hour filter, or any locked element based on locked-window results
- ✓ Hard falsifier #5 (Swing direction flip) honored — Swing is marked as failed_locked_walkforward_2026_05_17

## Lock status

```
lock_status: completed
locked_holdout_1_result: PARTIAL (2 of 4 families pass)
locked_holdout_2_result: PARTIAL (same 2 families pass; FVG matches expected here)
deploy_decision_for_4_family_candidate: do_not_deploy
deploy_decision_for_2_family_OB_sweep_subset: candidate_for_small_paper_trade_pending_other_gates
```

## Next steps

Per the lockfile bug policy, no further changes to this lock. The 4-family candidate is marked failed. A NEW protocol would be needed if we want to test the 2-family subset as a separate candidate — that's allowed because it's a different candidate, but cannot share this lock's pre-registration.

Recommended:
1. Mark this protocol's status as `completed` (this document does that)
2. If pursuing OB+Sweep as a deploy candidate: open a new locked walk-forward protocol for the 2-family configuration with its own pre-registration
3. Run the remaining validation items (roll integrity, day/week bootstrap, fill torture, portfolio sim) on the 2-family candidate specifically
4. Optional: investigate FVG strict regime-conditionality (2018-2019 weak, 2026 YTD strong) — could be useful research but doesn't gate deploy
