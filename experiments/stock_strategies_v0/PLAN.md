# PLAN — equities line (both strategies, end to end)

The program plan for getting **momentum_trend_v0** and **earnings_gap_v0** from scaffolds to
verdicts. Written 2026-06-18. This is the *sequence*; each strategy's SPEC is the *law*.

## Core architecture (why the plan is shaped this way)

The two strategies are **one execution engine + two setup detectors + shared models.**
They share the entire shell (1-min entry, stop=LOD, ½ partial→BE, trail/exit on close below
MA10/20, 1%/2% sizing, 30% cap, honest fills). So we build the expensive, error-prone part
**once**, prove it, then plug in cheap detectors. The discretion in both becomes **shared
models that must beat a simple-rule floor** or they don't ship.

Three rules govern everything:
1. **Floor-first.** Simple mechanical rules and dumb baselines before any ML. A model that
   can't beat the simple rule on dev-OOS across multiple periods is dropped.
2. **Honest or it didn't happen.** No-lookahead asserts at build time; honest fills
   (stop-vs-target tie → stop wins; gap-throughs honored); realized-R is the objective.
3. **Frequency/universe honesty.** NDX-100 (133 names, have it) is the *first pass*. A
   handful of setups is not a statistic — broaden the universe before any verdict.

## Dependency graph (what blocks what)

```
Phase 0 data ─┬─> Phase 1 SHELL ─┬─> Phase 2 momentum detector ─┐
              │                  └─> Phase 3 earnings detector ──┼─> Phase 4 MODELS ─> Phase 5 broaden ─> Phase 6 HOLDOUT ─> Phase 7 combine
              └─ earnings calendar ──────────^                   │
```
The shell (Phase 1) is the critical path — neither strategy can be tested without it.
Phases 2 and 3 are independent once the shell exists. Models (Phase 4) need the simple-rule
baselines from 2–3 to have something to beat.

---

## Phase 0 — Foundations & data  *(size: M — mostly DONE 2026-06-18)*

**Goal:** close data gaps, lock the §0 decisions, build causal loaders.

**DONE** (see [DATA_PULL_SPEC.md](DATA_PULL_SPEC.md) for the full inventory):
- ✅ Broad daily stocks: **527 ≈ S&P 500, 2010→2026, adjusted** (another chat, yfinance).
- ✅ ETFs for regime + sector models: SPY/QQQ/IWM/DIA + 11 XL* + SMH, 2010→2026 (`etf/`).
- ✅ Earnings calendar: 132/133 names, 1935 events, AMC/BMO + EPS surprise.
- ✅ Intraday 1-min RTH for the 133 NDX names (entry mechanic).
- 16 years of daily across many regimes = a **windfall for the cycle/rotation model**.

**DONE (2026-06-18, cont'd):**
- ✅ Broad universe **fully landed: 5,310 daily names (yfinance, 2010→2026)** — the small-cap
  turf the momentum strategy needs is now present.
- ✅ **Causal loaders built + tested** (`common.py`, `loaders.py`, `phase0_sanity.py` ALL
  PASS): `load_daily/etf/m1/earnings`, `history_up_to`, `with_mas`, raising `assert_no_lookahead`.
- ✅ **Source-consistency resolved** ([DATA_NOTES.md](DATA_NOTES.md)): yfinance daily =
  correctly split+div adjusted (verified vs real split history incl. BKNG 25:1, KLAC 10:1);
  ThetaData m1 = raw. No corruption in the core 131. **Reconciliation rule recorded** for the
  shell (run each trade in one price space; map m1 fills via the day's adj factor).
- ✅ **Data-quality screen** (`screen_daily_quality.py`): 32 broken → quarantined, 114 thin,
  948 micro-cap extreme-movers (handled by a detection-time liquidity/price filter).

**REMAINING for Phase 0 (small):**
- Lock decisions: universe filter (drop quarantine+thin, price/$vol floor — see DATA_NOTES),
  survivorship (disclose now, point-in-time Phase 5), premarket (defer to Tier C re-pull).
- The reconciliation itself is *implemented* in Phase 1 (the shell), per DATA_NOTES.

**Deferred (on-demand, not blocking):** 1-min for triggered non-NDX names + premarket
(ThetaData data-chat, after detectors produce a trigger list).

**Phase 0 status: effectively DONE.** Loaders + data certified; clear to start Phase 1 (shell).

## Phase 1 — Shared execution shell  *(size: L — the keystone)*

**Goal:** the engine both strategies run on, proven correct in isolation.

**DONE (2026-06-18) — Tier 1 daily-resolution core (`shell.py`, `test_shell.py` ALL PASS):**
- `Signal` in → `Trade` out; pure + deterministic. Lifecycle: enter (next-open / signal-open)
  → LOD stop (buffer) → ½ partial into strength at day +3–5 → stop to breakeven → MA10/20
  trail/exit. Honest fills: **stop checked first (wins ties), gap-throughs fill at the open,
  costs both sides**, `fill_confidence='daily'`, MAE/MFE in R. `size_position` (1% risk, 30%
  exposure cap). `run_signals` batches over the universe.
- Verified on synthetic hand-built series (winner+partial+trail, stop ≈ −1R, gap-through
  < −1.5R, **stop-wins-the-tie**, **determinism**) AND smoke-tested on real adjusted data
  (NVDA stop −1.00, AAPL trail +1.77, AMD BE +0.25, MSFT stop −1.00).

**REMAINING (deferred by the two-tier design):**
- **Tier 2 — m1 intraday-entry refinement** (NDX subset): true first-1-min-candle trigger,
  mapped into adjusted space via the day's adj factor → fill-realism convergence check.
  Slots into **Phase 3** (honest fills), not blocking Phase 2.
- Portfolio/equity sequencing (shared capital, concurrent positions) → **Phase 4**. The
  per-trade core returns R, which is account-independent, so this is a thin layer on top.

**Done when:** ✅ known entries produce hand-verifiable, deterministic, honestly-filled
trades. (Tier-1 met. Tier-2 fill realism rides in Phase 3.)

## Phase 2 — Momentum detector (simple mechanical)  *(size: M)*

**Goal:** first realized-R read on the dumb version of strategy 1.

- Build the setup detector (SPEC §3): thrust → tight base into rising 10/20MA on drying
  volume → narrow-range run-in → MA alignment → not-extended → breakout (volume > prior,
  close near HOD) → tradability screen (ADR%/ATR; float when available).
- Run through the shell. **Baselines to beat:** buy-and-hold same names; naive "buy any
  20-day-high breakout, stop LOD." Purged **walk-forward** + **shuffled-target control**.
- Report realized R, equity curve, **setup counts/frequency**, drawdown vs the claimed
  ~30%-win/3–4:1/~20%-DD profile.

**Done when:** LEDGER entry with the simple-rule verdict + the baseline it must beat.

**DONE (2026-06-18) — first read in `momentum_trend_v0/{detector.py,run_phase2.py}`:**
HTF (n=173): trimmed-mean −0.01, median +0.02, win 53%. Naive floor: trimmed −0.14, median
−0.83, win 43%. **HTF beats the floor (+0.13 trimmed, +10pp win, median −0.83→+0.02) but is
~flat absolute.** Caught+fixed a near-zero-risk stop bug en route (LEDGER). PROMISING but
UNVALIDATED — needs the §8.4-8.5 rigor next. The ~flat base is exactly what the Phase 4
setup-quality model is meant to select from.

**REMAINING before trusting it:** walk-forward (purged/embargoed) + shuffled-target control
+ per-year consistency; tighten naive's junk screen; consider survivorship impact. Then
exit-style review (current partial+BE+trail = high-win/low-R vs the doc's 30%-win/3-4:1).

**VERDICT (2026-06-18): MOMENTUM PARKED — NULL.** Validation killed the +0.13 (CI includes
0 and the floor). Exit-style sweep: no edge under any exit. Model-free continuation study
(643k breakouts, market-relative): breakouts **MEAN-REVERT** here, worst in the high-thrust/
high-ADR names the doc targets; only <$10 faintly positive (survivorship-contaminated). A
negative base rate can't be rescued by selection models → **do NOT build the momentum models.**
Pivot to earnings (Phase 3) or get non-survivorship data first. Durable assets kept: the
shell, detector, and study harness (all reusable). See LEDGER 2r.

## Phase 3 — Earnings detector (simple mechanical)  *(size: M)*

**Goal:** same, for strategy 2.

- Earnings-day gap detector (SPEC §3): gap > 7.5%, open > prior high, gap **above**
  resistance (not into it), long prior base, above-avg volume, liquidity screen.
- Run through the shell. **Baseline:** buy every earnings gap > 7.5%, stop LOD. Walk-forward.
- Report realized R, **setup counts** (expected LOW on NDX-100 — this is the loudest signal
  that we need the broader universe), reproduce-claimed-stats check (~40%-win/3:1/~14%-DD).

**Done when:** LEDGER entry + verdict on the simple earnings rule, with an explicit note on
whether frequency is sufficient for statistics.

## Phase 4 — Model the discretion  *(size: L — the real research)*

**Goal:** replace folklore with models that *measurably* beat the Phase 2–3 floors.

Build in this order (most direct lift first), each causal + purged-WF + shuffled-control +
**ablated against its simple-rule floor**, realized-R objective:

1. **Setup-quality model (momentum)** — P(breakout follows through to target R) from setup
   features. Feeds an EV/threshold trade layer.
2. **Gap-continuation model (earnings)** — P(gap continues vs. fades) from gap features.
   This is the "stay out of the bad gaps" engine — the core of strategy 2's edge.
3. **Strength/weakness model (shared)** — cross-sectional RS ranking of sectors + stocks →
   a leadership feature for both detectors.
4. **Cycle/rotation + regime model (shared)** — market phase / risk-on-off → gates both;
   must beat the simple SPY/QQQ 10v20MA rule.

**Done when:** for each model, a LEDGER verdict: does it beat its floor on dev-OOS across
multiple periods? Keep the ones that do; the simple rule stays where they don't.

## Phase 5 — Universe expansion & robustness  *(size: M, gated on Phase 4 promise)*

- If results are promising: pull the **broader liquid-US universe** (+ point-in-time
  membership to kill survivorship), re-run both detectors + kept models, check **consistency
  across cohorts**.
- Cost/slippage **stress** (gap-day opens are wide — stress harder), fill-realism re-check.

**Done when:** the edge (if any) holds on a fair universe with stressed costs, or it doesn't.

## Phase 6 — Sealed holdout & verdict  *(size: S, but irreversible)*

- Register primaries, then spend a **holdout read** (budget: 2 lifetime, logged). One per
  strategy. This is the final word.
- Verdict per strategy: deploy-paper / iterate-once / shelve.

## Phase 7 — Combine (optional, if both survive)  *(size: M)*

- The author runs them together → a **combined portfolio sim**: shared capital, both
  detectors, regime-gated, realistic sizing. The equity curve of the *system*, not the parts.

---

## Recommended sequence & first step

Build order is forced by the dependency graph: **Phase 0 → Phase 1 (shell) → Phase 2
(momentum) → Phase 3 (earnings) → Phase 4 (models) → 5 → 6 → 7.**

- **Momentum before earnings** as the first detector: it's self-contained (no earnings-
  calendar dependency) and exercises every part of the shell, so it shakes out engine bugs.
- **First concrete step:** Phase 0 data + Phase 1 shell. Everything downstream needs them,
  and the shell is where correctness is won or lost.

## Open decisions (recommended defaults — override anytime)

| # | Decision | Recommended default | Why |
|---|---|---|---|
| D1 | Universe for v0 | NDX-100 (133, have it) first; broaden in Phase 5 | Start free/fast; broaden once there's something worth fairness |
| D2 | Survivorship | Disclose bias in v0, point-in-time in Phase 5 | Don't let it block the first read |
| D3 | Earnings source | yfinance v0 (audit coverage) | Free, installed; upgrade only if coverage is bad |
| D4 | Premarket | RTH-open gap v0; extended-hours re-pull later | Gap is computable now; premarket volume is a refinement |
| D5 | Build ML in-repo | LightGBM (already in `backend/.venv`) | Matches the futures lines; tabular-first per SPEC |

## Rough effort shape

Phase 1 (shell) and Phase 4 (models) are the heavy lifts. 0/2/3 are moderate, 5/6/7 lighter
or gated. The shell is reused by everything, so time spent there pays back twice.
