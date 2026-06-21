# LEDGER — momentum_trend_v0

Append-only. Every registered construction: what was tested, the result, the verdict, and
the diagnosis (which component, with the evidence that distinguishes it from "no edge").
Per SPEC §8.10, each construction gets one revision cycle, then its verdict locks.

| Date | Phase | Construction | Result | Verdict | Diagnosis |
|---|---|---|---|---|---|
| 2026-06-18 | — | Source doc ingested, mechanized into SPEC. No code/tests yet. | — | — | Awaiting §0 decisions + doc 2/2. |
| 2026-06-18 | 2 | Simple HTF detector (thrust+tight base+near-HOD breakout) vs naive 20d-high floor, daily shell, dev≤2025-09-30, pooled | HTF: n=173, trimmed-mean −0.01, median +0.02, win 53%. Naive: trimmed −0.14, median −0.83, win 43%. HTF−floor = +0.13 | PROMISING, UNVALIDATED | Structure looked like it beat the floor; flagged for validation before belief. |
| 2026-06-18 | 2v | VALIDATE the above: per-year consistency + name-block bootstrap, winsorized [-1.5,+10] R | HTF wmean +0.067, 90% CI **[−0.105, +0.250]** (includes 0 AND the floor); win 52.6% CI [46,59] (includes 50%); only **7/16 years positive**. Naive floor wmean **+0.008** (≈0 under the same metric). | **NO DEMONSTRABLE EDGE** | The "+0.13" was an artifact of trimmed-mean vs the naive fat tail; under a robust metric naive≈0 too and HTF is indistinguishable from both 0 and the floor. Simple HTF rule = a wash. Carried by 2012 & 2025; no year-to-year consistency. Survivorship-biased base. Verdict LOCKED for the simple rule. |
| 2026-06-18 | 2e | EXIT-STYLE sweep on the same 173 signals (6 configs: ½-partial/BE/trail MA10; run-MA10; run-MA20; run-MA20+BE; target-3R; target-5R), bootstrap CI | 'Run' styles reproduce the doc's low-win (28-36%)/fat-tail (7-9% are ≥3R) SHAPE. All wmean 90% CIs include 0 **except target-3R** (+0.218, CI [0.018, 0.427]). | **NO EDGE (any exit)** | Exit style changes the win/R SHAPE but not the bottom line — still a wash. target-3R is almost certainly a multiple-comparisons artifact: 1 of 6 configs, CI barely clears 0, and its neighbor (5R) is null. Momentum's only remaining path = selection MODELS (leadership/regime/quality), per the 'model the discretion' thesis. |

| 2026-06-18 | 2r | RETHINK (Ben's call): model-free continuation study, **643,256** breakouts (10d-high), MARKET-RELATIVE (excess vs SPY), dev window, sliced by thrust/ADR/price | Excess forward return **NEGATIVE at every horizon** (all: x5 −0.19% / x20 −0.41% / x40 −0.69%, win ~47%). **WORST exactly in the doc's turf:** >100% thrust → x40 **−4.23%** (win 39%); >8% ADR → x40 **−5.30%** (win 37%). Only <$10 faintly positive (x40 +0.43%, win 47%) — and that's the most survivorship-contaminated slice. | **MOMENTUM NULL — breakouts MEAN-REVERT here** | The setup has a NEGATIVE base-rate edge → no selection model can fix a negative base. The explosive/volatile names the strategy explicitly targets revert hardest. Survivorship bias means reality is worse, not better. Mechanical momentum on this universe = dead. → STOP building momentum; pivot to earnings (PEAD has a far stronger prior) or get non-survivorship data first. |

| 2026-06-18 | 2r-short | Re-check (Ben: 'test momentum w/ new intraday'): extend continuation study to SHORT horizons 1/2/3-day — is there fast follow-through before the mean-reversion that intraday could catch? (run_continuation_study.py HZ=[1,2,3,5,10,20]) | NEGATIVE from DAY 1 in every thrust/ADR/price bucket. >100% thrust x1d −0.28% / x3d −0.72%; >8% ADR x1d −0.67% / x3d −1.61%; win3d ~43-49%. No pop-then-fade — fades immediately. | **MOMENTUM DEAD AT ALL HORIZONS (1-40d)** | Intraday entry can't rescue a setup negative from day 1 (nothing to enter into). New intraday data won't help momentum → do NOT pull it for momentum. Only remaining re-test = survivorship-clean (free w/ daily_pit), but survivorship typically INFLATES breakouts → clean data likely confirms/worsens the NULL. Momentum stays parked/dead. |

## Notes / running log

- **2026-06-18** — Strategy 1/2 ingested from the sartrading PDF and translated to a
  mechanical SPEC. Open before Phase 1: research path (§0.1), universe breadth (§0.2),
  survivorship basis (§0.3). Known data gaps: SPY/QQQ (regime), sector data (leadership).
- **2026-06-18 (Phase 2)** — First detection read. CAUGHT A MEASUREMENT BUG first: stop was
  the next-open entry-day low → tiny-range days gave near-zero risk → fake huge R (MEDP +283R
  on a 0.8% move; trades with risk<1% averaged +8.7R vs −0.06R for risk≥1%). FIXED: stop =
  breakout(signal)-day low + 0.5% min-risk floor (shell.py); shell test still green. Corrected
  result above. Naive max_R still 1992 (micro-cap junk) but trimmed-mean comparison + HTF's
  stricter filter (max 14.9) handle it. NEXT: validate HTF-beats-floor with walk-forward +
  shuffled-target control + per-year consistency before trusting +0.13; then setup-quality
  model (Phase 4) to select the good setups out of this ~flat base; consider exit tuning
  (our partial+BE+trail yields high-win/low-R, vs the doc's 30%-win/3-4:1 profile).
- **2026-06-18** — Read all diagrams (DIAGRAMS.md). Refinements folded into SPEC:
  partial 25–50%+BE, runner exits on first daily close < MA10, explicit re-entry rule,
  ADR%/ATR/low-float character screen, MA50/EMA200 context. Direction set (Ben): model the
  discretion → SPEC §6.5 (strength/weakness, cycle/rotation, setup-quality models). Added
  data gap 3 (float/earnings). Diagram example names (HUT/UROY/AMR/SI) confirm the
  universe-breadth gap — they aren't in NDX-100.
