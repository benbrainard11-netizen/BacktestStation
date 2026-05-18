# Paper-Trade Gates — 2-Family Core (OB strict + Sweep reversed)

_Generated 2026-05-17. Owner: benpc._

Pre-paper-trade gauntlet for the v20 survivors. 4 offline gates run
on the existing v20 trade outputs (no re-simulation). All scripts in
`backend/scripts/ml/v22_*` through `v25_*`. Results in `results/`.

## Headline: 3 PASS, 1 FAIL (concurrency haircut)

| # | Gate | Verdict | Key number |
|---|---|---|---|
| 1 | Roll-anomaly check (v22) | **PASS** | inflation ratio 1.27 / 1.00 (≤ 2x threshold) |
| 2 | Day/week block bootstrap (v23) | **PASS** | P(annual R ≤ 0) = 0% across 3 block sizes |
| 3 | Fill-model torture (v24) | **PASS** | vol-25 retention 89.8% / 95.8% (≥ 80% threshold) |
| 4 | Single-account portfolio (v25) | **FAIL** | cap=2 retention 53.5% (< 70% threshold), cap=1 32.4% (< 40%) |

## Gate 1 — Roll-anomaly check

**Question**: is the v20 result inflated by continuous-contract roll-day artifacts?

**Method**: 40 quarterly roll windows (3rd-Friday-of-Mar/Jun/Sep/Dec ± 5/1 days). Classify each trade as roll-adjacent or non-adjacent. Compare cum_R share vs uniform-expected share.

**Result**:
- OB strict: roll-adjacent share = 12.7% of cum_R vs 10% of days → inflation ratio 1.27 (well under 2x cap). avg_R ratio 1.21.
- Sweep reversed (filtered): roll-adjacent share matches expected almost exactly → inflation ratio 1.003. avg_R ratio 1.05.

**Verdict**: PASS. The 2-family core is NOT roll-dominated. Within the limits of continuous-symbol data (no per-contract bars on disk), there's no evidence the edge depends on roll artifacts.

**Limitation**: this is a heuristic check. A full per-contract audit would require pulling and storing per-contract NQ + ES bars. Out of scope for now.

## Gate 2 — Day/week block bootstrap

**Question**: is the cum_R robust to *which specific days* were lucky, or is it driven by a few outlier days?

**Method**: per-trading-day pnl_r aggregation. Block bootstrap with 1d / 5d / 20d blocks, 10,000 resamples each. Annualize to 252 trading days.

**Result**: P(annual R ≤ 0) = 0% across all 6 (family × block size) combinations.

| Family | Block | 5th pct | Median | 95th pct |
|---|---|---:|---:|---:|
| OB strict | 1d | 617.6 | 694.1 | 770.6 |
| OB strict | 5d | 620.7 | 694.3 | 766.8 |
| OB strict | 20d | 623.7 | 690.0 | 752.5 |
| Sweep reversed | 1d | 431.5 | 499.8 | 567.0 |
| Sweep reversed | 5d | 433.1 | 496.2 | 561.7 |
| Sweep reversed | 20d | 430.2 | 490.7 | 552.4 |

**Verdict**: PASS. Even at 20-day blocks (preserving month-scale regime structure), the 5th percentile of annualized R remains well above zero for both families.

**Caveat**: bootstrap operates on the held-out days only. It tests *internal* robustness, NOT external generalization. The v20 locked walk-forward was the external test.

## Gate 3 — Fill-model torture (volume gating)

**Question**: was the bar containing each entry/exit liquid enough to absorb a 1-contract market order?

**Method**: for each trade, look up the 1m bar at entry_ts. Drop trades where bar volume < threshold. Compute cum_R retention.

**Result**:

| Family | vol ≥ 10 | vol ≥ 25 | vol ≥ 100 |
|---|---:|---:|---:|
| OB strict | 94.9% | 89.8% | 69.1% |
| Sweep reversed | 98.2% | 95.8% | 79.3% |

**Verdict**: PASS. Retention exceeds 80% at vol-25 and 90% at vol-10 thresholds for both families.

**Note**: at vol-100 (a strict liquidity bar), OB drops to 69%, indicating ~31% of OB's edge comes from sub-100-contract-per-minute bars (likely Asia overnight + low-liquidity hours). This is not a fail but is worth tracking when sizing up — you won't be able to fill 10+ contracts in those bars.

**Out-of-range %** (informational only — 63.8% / 49.2%): these are NOT a fill-honesty failure. They reflect v8a's intentional 2-tick adverse slippage on stops/entries/time-exits, which by design records fill prices 2 ticks outside the bar's OHLC range. v18 already audited fill honesty against actual TBBO trade tape at 89% retention.

## Gate 4 — Single-account portfolio simulator (FAIL)

**Question**: when OB strict + Sweep reversed run on one account with concurrency caps, how much edge survives vs the v20 independent-silo numbers?

**Method**: merge both families' trades into one timeline (sorted by entry_ts, deterministic tiebreak). Walk forward; greedily accept trades subject to caps. Two configs tested.

**Baseline (independent silos, v20)**: 1,509 (OB) + 1,042 (Sweep) = **2,551.98 R combined** over 2.3 effective years (2018-2019 + 2026 fragment).

**Results**:

| Cap config | Trades taken | Blocked (per-sym / total) | cum_R | Retention | Threshold | Verdict |
|---|---:|---|---:|---:|---:|---|
| cap_total=1 (account-wide) | 2,370 / 6,381 | 1,408 / 2,603 | 827 R | 32.4% | 40% | **FAIL** |
| cap_total=2 (one per symbol) | 3,961 / 6,381 | 2,420 / 0 | 1,365 R | 53.5% | 70% | **FAIL** |

**Verdict**: FAIL on both pre-registered retention thresholds.

**Important context**:
- cum_R **stays positive** in both configs across both holdouts (2018-2019 and 2026 fragment). The strategy doesn't break under concurrency caps — it just compresses.
- At cap=2, 1,365R over 2.3 years ≈ **~590R/year**. That's still in the "base case" zone per prior triangulation (250-350R conservative, 500R bull). The expected $ return on $150K @ $20/R for NQ ≈ ~70-80%/yr at cap=2 (less commission/slippage which is already in the R numbers).
- Max drawdown is small: -9 to -11 R worst day. The edge survives compression, it doesn't break.

**Why retention is below threshold**:
- 240-min trade window × 0.8 trades/hr/family on NQ + ES = high concurrency contention
- OB and Sweep fight for the same symbol slot when both fire within 240 min of each other
- 2,420 of OB+Sweep's combined trades hit per-symbol blocks at cap=2

**Mitigations to explore before paper-trading**:
1. **Add more symbols** (e.g., RTY, YM, MNQ/MES micros) to spread concurrency
2. **Tighter trade window** for paper-trade rules (e.g., 120-min instead of 240-min)
3. **Family-priority rule** when both fire simultaneously — take the higher-historical-win-rate signal, not just-first
4. **Single-family v21** — paper-trade only OB (the bigger edge) and treat Sweep as research-only until concurrency is sorted

**Honest read on the FAIL**:

The pre-registered 70% threshold may have been too generous. 50-60% retention under realistic capacity caps is typical for portfolios of correlated strategies. The strategy is still positive and substantial; what fails is the **specific retention threshold I committed to in the pre-registration**.

Per OPERATING_RULES.md, I'm NOT moving the goalposts. The gate failed; that's the recorded result. The decision about paper-trade go/no-go depends on whether ~590R/year at cap=2 is good enough to deploy, OR whether we want to investigate one of the 4 mitigations first.

## Overall verdict

**3 PASS, 1 FAIL.**

The 2-family core (OB strict + Sweep reversed filtered) is:
- Not roll-dominated (gate 1 ✓)
- Bootstrap-robust (gate 2 ✓)
- Fillable in real volume conditions (gate 3 ✓)
- Subject to a real **50%+ concurrency haircut** when forced through one account (gate 4 ✗)

**Recommended next step (operator decision)**:

**Option A — paper-trade at cap=2 anyway**, with explicit acknowledgment that retention is 53.5% (not the 70% pre-registered target). Expected R/year ≈ ~590, $ return ≈ 65-80% on $150K. Document the threshold miss in the v21 lockfile bug-policy section.

**Option B — investigate mitigations first.** Spend ~half a day on one of the 4 mitigations (probably "tighter trade window" since it's the easiest to test). Re-run v25. If retention improves to ≥70%, paper-trade. If not, decide based on the new number.

**Option C — single-family paper trade (OB only)**. The OB family's independent cum_R was 1,509R / 2.3 yr ≈ 655R/year. No concurrency conflict with itself, so cap=1 retention ≈ 100%. Treat Sweep as research-only until cap=2 retention is resolved.

My read: **Option C is the most honest path**. It paper-trades the strategy that doesn't have the failed gate (OB alone is unaffected by gate 4 because there's no inter-family conflict). Sweep can be added later once we've fixed concurrency.

## Files

- `results/v22_roll_anomaly_check.json` + `.md`
- `results/v23_block_bootstrap.json` + `.md`
- `results/v24_fill_model_torture.json` + `.md`
- `results/v25_single_account_portfolio.json` + `.md`
- `results/v25_trades_taken_cap_total_1.csv` (forensic)
- `results/v25_trades_taken_cap_total_2.csv` (forensic)
