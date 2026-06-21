# Overnight report — 2026-06-02

You authorized three things: (1) the extended Mira MBO validation, (2) the data gap-fill, (3) build the
energy RV bot. Here's the honest scoreboard. **The headline: the Mira MBO edge is now confirmed on a real
backward OOS slice with my own honest machinery, and the energy RV bot is built and proven robust.**

---

## 1. Mira MBO validation — the milk bottleneck. CONFIRMED (with one important correction)

**I had to kill my own original plan.** "Extend the OOS to Feb–May 2026" was *wrong*: the frozen model
trained on **2026-02-06 → 2026-05-20**. So Feb–May is the model's *training data* — testing there would have
been testing on the training set (lookahead) and produced a fake-good number. The genuine out-of-sample slice
is **January 2026** (before the training window). I caught this by reading the model's own train-window metadata
before running anything.

**What I actually did:** the Jan with-MBO entry set (139 real entries) had never been run through our honest
exit machinery — the +0.38R was a number in memory. So I ran the *exact same* exit logic used on the MBO-free
baseline (stop-wins-ties, $3.80 commission + 2-tick stressed slippage, trail-2R) on the 139 Jan entries.
Apples-to-apples:

| entry set (same machinery) | n | win% | mean R (trail_2R) |
|---|---|---|---|
| MBO-free 2025 OOS | 909 | 34% | **−0.110R** (loser) |
| **WITH-MBO Jan-2026 OOS** | 139 | 50.4% | **+0.439R** |

**Delta +0.549R. The MBO edge is real and reproduced.** (fixed_2R = +0.378R, matching the remembered +0.38R
exactly; trail_2R is better.) Script: `sizing_v1/replay_jan_withmbo.py`.

**Honest caveats:**
- It's **one month** (Jan 2026, n=139). A genuine pre-training OOS slice, decent sample, but one regime.
- The **forward** slice (May 21–27, post-training) is *not* runnable tonight: it needs Mira's SMT +
  volume-profile features regenerated for that window (they're not on disk; Jan reused a cached `combined`),
  which means excavating Mira's pipeline in a repo another agent may be using. Not worth the risk for ~5 days.
- **The clean way to get more OOS is to pull more *pre-training* MBO (Oct–Dec 2025)** — same proven pipeline,
  earlier dates, could 3–4× the sample. That needs your explicit MBO-pull approval (the safety classifier blocks
  it). **This is the #1 thing to greenlight when you're up.**

### Milk projection on the CONFIRMED distribution (`sizing_v1/fleet_mira_confirmed.py`)
40 staggered Apex accounts, ~5-month cohort, net of fees, using the *real* 139-trade shape (not a synthetic shift):

| distribution | $75/R | $150/R | $300/R | blow rate (75/150/300) |
|---|---|---|---|---|
| MBO-free (−0.11R) | −$14k | −$13k | −$10k | 97% / 100% / 100% (dead) |
| **WITH-MBO Jan (+0.44R)** | **$470k** | **$1.04M** | $1.94M | 0% / 2% / 11% |
| WITH-MBO halved (+0.22R, stress) | $208k | $401k | $597k | 8% / 28% / 54% |

If the edge holds → ~$1M per cohort at the $150/R sweet spot (2% blow, $768k 5%-tile). Even at **half** the
edge it's $200–400k. MBO-free is dead at every size. Conservative sizing ($75–150/R) is the play; $300/R blows
54% under the stress case. **Bootstrapping one month to annual fleets assumes Jan generalizes — it's the best
evidence we have, not proof. More OOS (the MBO pull) is what turns this from "promising" into "fund it."**

---

## 2. Energy RV bot — BUILT, validated, robust. The deployable non-Mira edge.

`energy_rv_v0/energy_rv_bot.py` — a runnable daily-rebalanced bot from the cointegrated energy spreads.

**Continuous book reproduces the research exactly** (signals/PnL on the validated `daily_returns.parquet`):

| book | full Sharpe | **OOS Sharpe** | CAGR | maxDD |
|---|---|---|---|---|
| Full energy (5 pairs, HO/RB dropped) | +0.56 | **+0.59** | +8.7% | −34% |
| **CL/BZ only (the star)** | +1.13 | **+1.54** | +19.5% | −17% |

**Robustness (`robustness.py`) — not overfit:** OOS Sharpe is **100% positive across all 9 (BETAWIN×ZWIN)
cells** for both books (CL/BZ min +1.44 / median +1.68; full book min +0.74), and survives cost stress to 8bp
(CL/BZ +1.09, full +0.51). This is a parameter-insensitive structural edge — the opposite of the chart-pattern
stuff that died.

**Two real findings:**
- **CL/BZ alone beats the diversified book** (OOS +1.54 vs +0.59, half the drawdown). Your instinct to start
  with CL/BZ was right — the "diversification" of the other pairs dilutes more than it helps.
- **A $30k account is too granular to trade this.** Energy futures are $70–100k notional each, so at a 12% vol
  target a $30k account holds ~0.1–0.6 contracts (mostly flat, lumpy). Integer execution tracks the continuous
  book cleanly only at **~$75k (CL/BZ)** / **~$150k (full book)**. Below that you need micros (MCL exists; no
  micro Brent/HO/RB, so micros only partly help) or a higher vol target (defeats the high-floor point).

Deployable artifact: `energy_rv_v0/out/energy_rv_positions.parquet` (daily target contracts + equity, $150k acct).

---

## 3. Data gap-fill — ran SAFE, filled little (and that's correct behavior)

`gap_filler` ran with its $0 guardrail intact. It **never charged anything**. Two things happened:
- Most days returned a `$nan` per-symbol cost estimate → the guardrail correctly **skip-warned** them (it
  refuses to pull anything it can't verify is free). Safe, conservative, but means little got filled.
- Palladium/platinum (PA/PL) recent days returned **"no data"** — those symbols genuinely have no recent
  Databento coverage (or the `.c.0` continuous mapping has no current contract).

Net: the guarded gap-fill is working as designed (free-or-nothing), but the per-symbol-day cost check is too
unreliable (`$nan`) for it to fill much autonomously. **To actually fill gaps you'll want to approve a
specific, price-checked pull** (the multi-symbol cost check *is* reliable — your full plan priced at $0).

---

## 4. Data-quality bug found (flagged, not yet fixed)

While building the energy bot I found that **`read_bars` → `resample("1D").last()` mis-prints ~30 roll/crash
days**: e.g. it shows CL **+3.8%** on the 2021-11-29 Omicron crash when crude actually fell ~9% (the validated
`daily_returns.parquet` has −8.9%). The UTC day-boundary grabs a wrong/thin 1-min print on roll and extreme-vol
days, **understating volatility** (CL daily std 0.031 vs the correct 0.035) and even flipping the CL/BZ spread
sign (−0.08 vs the true +1.54). I worked around it (signals/PnL use the validated returns file; `read_bars`
levels are used only for contract sizing), but **the daily-close resampling needs a session-aware fix before it
can be trusted as a signal source.** This affects any daily strategy built off fresh `read_bars` resampling.

---

## Recommended order when you're up
1. **Approve a pre-training MBO pull (Oct–Dec 2025, 4 index symbols)** — the single highest-value move; turns
   the Mira edge from "one confirmed month" into a real multi-month OOS that justifies funding the milk fleet.
2. **Decide the energy bot's home** — CL/BZ at ~$75–150k is the cleanest live-account starter (OOS Sharpe ~1.5,
   −17% maxDD, market-neutral). It's the "grow a real account" sleeve, uncorrelated to Mira.
3. **Fix the daily-close resampling bug** (or confine daily strategies to `daily_returns.parquet`) before
   building any new daily strategy on fresh `read_bars` data.

Scripts written tonight: `sizing_v1/replay_jan_withmbo.py`, `sizing_v1/fleet_mira_confirmed.py`,
`energy_rv_v0/energy_rv_bot.py`, `energy_rv_v0/robustness.py`.

---

## Follow-up (same day) — fragility of the +0.44R + live eval context

**The live engine IS the real edge.** Read the `live_engine/` repo: `features_source: rithmic_mbo`
(true order-by-order depth via async_rithmic), frozen 139-feature model, trail-2R / $75-per-R / micros,
and a HARD rule `halt_on_feature_unavailable` → it refuses to trade on degraded features. So it's the
+0.44R edge or nothing — structurally cannot run the −0.11R MBP-1/structure-only loser. Open gap: the
engine's own final check (Leg-B parity, Rithmic-MBO == Databento-MBO features) was never actually run —
only an 8-sec ES smoke recording exists, and no overlapping Databento MBO to compare to (ends 5/27).
The live eval is now the de-facto parity + forward test. (Order *execution* is the live blocker — being
fixed on another PC; 3 manual trades so far.)

**Fragility stress-test of the confirmed +0.44R** (`sizing_v1/mira_jan_fragility.py`, 139 Jan trades):
- **Bootstrap (50k):** mean R 5th/50th/95th = **+0.199 / +0.437 / +0.685**; P(mean>0)=**99.9%**,
  P(mean>+0.20R)=**95%**. Robustly positive *within January*.
- **Broad, not concentrated in one place:** all 4 symbols positive + similar (+0.38…+0.56, ~50% win
  each); both long (+0.52) and short (+0.36) positive.
- **Survives worse costs:** +4 ticks/trade extra slippage → still +0.218R.
- **Intra-month path:** max drawdown only **−7.5R** (−$566 at $75/R, −$1,132 at $150/R) vs a ~$2-2.5k
  prop trailing DD → would NOT have blown an account mid-January. Worst losing streak 6.
- **Caveat (the one yellow flag):** positive-skew — top 10 trades = 66% of total R; remove the best 20
  and it's −0.08R. That's the normal signature of a let-winners-run (trail-2R) exit, but it means
  month-to-month P&L will be lumpy and depends on catching the big runners.

**Live 3 trades vs Jan** (`-1R / 0R / +3.5R`, +2.5R): each falls at its expected Jan percentile (49th /
50th / 94th); the +2.5R sum is a normal upper-third 3-trade outcome (34% of random Jan triples beat it).
**Consistent with the backtest — tracking, no red flag.** n=3, so context not proof.

**Net:** the milk plan's load-bearing number is robust *within* January (broad, cost-resistant,
low-drawdown) and the early live fills look like backtest fills. The only thing still missing is
cross-month OOS — which the live eval is now generating for free, trade by trade. Bottleneck = getting
auto-execution working (other PC).

---

## Follow-up 2 — the RV bot should be DIVERSIFIED, not energy-only

Tested whether economically-grounded diversification beats the energy book (`energy_rv_v0/
diversified_rv_book.py`). Four uncorrelated structural-spread complexes, each independently validated,
2bp/leg, OOS 2023+:

| complex | pairs | OOS Sharpe | maxDD |
|---|---|---|---|
| energy (crack + Brent-WTI) | 5 | +0.93 | −34% |
| grains (corn/soy/wheat crush) | 3 | +1.10 | −15% |
| curve (ZF/ZN/ZB/ZT) | 3 | +0.82 | −3% |
| metals (gold/silver) | 1 | +0.60 | −25% |
| **combined (equal-risk)** | 12 | **+1.44** | **−14%** |

**Diversification clearly wins: +0.93 (energy only) → +1.44 combined, and the drawdown halves.** Robust:
positive every OOS year (+1.0…+1.8, only 2020 flat), 100% positive across all 9 (BETAWIN×ZWIN) cells.
The complexes **rotate** — 2025 grains went flat (+0.03) while metals carried (+1.61); no single complex
is load-bearing. That's genuine diversification across independent edges (refining arb ⟂ crush ⟂ yield
curve ⟂ gold/silver), not a Sharpe-mine — pure-ADF selection (which drags in spurious YM/HG, ES/HG) only
gets +0.46; choosing pairs by *economics* gets +1.44.

**Caveats:** (1) assumes ~2bp/leg — grains/curve/metals are less liquid than energy/equity, so real
slippage would haircut it (energy/CL-BZ stays the most liquid/robust leg). (2) 12 pairs across ~10
symbols needs *more* capital than energy alone for clean integer execution — even further from a small
account. So this is the "best RV strategy for when capital/a swing-account exists," and CL/BZ remains the
simplest liquid starter. The validated book lives in `diversified_rv_book.py` (return-space; add the
`energy_rv_bot.py` sizing layer when there's capital to deploy).
