# ORB Pre-Holdout Verification — GO / NO-GO

**Date:** 2026-06-20
**Scope:** Three pre-registered ORB survivors, each entitled to ONE sealed-holdout shot
(holdout window 2025-06-10 .. 2026-06-09, untouched by all checks below).
**Inputs consolidated:** code review (look-ahead + fill honesty), MBP-1 tick fill verification,
robustness (block-bootstrap + stress).
**Engine / sweep:** `experiments/prop_futures_v0/orb_engine.py`, `experiments/prop_futures_v0/sweep.py`.

A GO requires ALL of:
1. Code review found no high-severity look-ahead / fill bug (only fixable caveats, listed in must-fix).
2. MBP-1 fills not materially optimistic (small mean entry slip, fill_rate high, verified sample
   net_R not collapsing vs modeled).
3. Robustness OK (bootstrap P(edge>0) reasonably high, not single-year-dependent, survives the
   entry-bar-include stress AND a 2-tick slip stress).

Conservative bias: if a config's edge sits inside the bootstrap noise, flips on +1 tick of cost,
or depends on the lenient entry-bar convention, it is NO-GO.

---

## Candidate table

| Symbol  | OR (min) | target_R | vol_gate   | gate_thr (ticks) | design net_R |
|---------|---------:|---------:|------------|-----------------:|-------------:|
| CL.c.0  |       30 |      0.0 | none       |              —   |       +0.027 |
| ES.c.0  |       30 |      0.0 | prior_atr  |          166.329 |       +0.086 |
| RTY.c.0 |       15 |      2.0 | none       |              —   |       +0.026 |

Design net_R reproduced exactly by the robustness harness (CL 0.0272 vs 0.027, ES 0.0858 vs 0.086,
RTY 0.0263 vs 0.026); the ES prior_atr gate re-derived to 166.329, matching pre-reg. Harness is faithful.

---

## Verification stream 1 — Code review (look-ahead + fill honesty)

**Verdict: SAFE FOR HOLDOUT. No high-severity bug. `look_ahead_clean = true`, `fill_honesty_clean = true`.**

Both files read in full, self-test ALL PASS, plus 5 custom probe scripts
(`_scratch/probe_audit.py`, `probe_gate.py`, `probe_sweep.py`, `probe_realdata.py`).

Clean on all five required look-ahead checks:
- (a) OR uses only `[open, open+or_minutes)`.
- (b) breakout detected only in post-OR / pre-cutoff bars on each bar's own high/low, filled
  gap-aware at the trigger/open (worse), never a future bar.
- (c) management starts at `ei+1`, skipping the entry bar **symmetrically** for stop and target
  (mirrors the canonical broker) — NOT directionally optimistic on the stop-vs-target axis.
- (d) `or_width` uses only the OR; `prior_atr` uses `.shift(1)` (a day provably never enters its own
  gate; spike test confirmed) with exact index alignment.
- (e) `derive_gate_threshold` is computed on the design df only and carried into the holdout as an
  absolute threshold — holdout never re-derives (no boundary leak).

Fill honesty (CLAUDE.md rule 8): same-bar stop+target takes the conservative stop (`stop_ambig`,
verified both sides); entry slip adverse; stop exit slipped adverse while target (resting limit) is
not; commission charged; gap-open-beyond-trigger fills at the worse open. Deterministic / byte-identical.

Issues found are robustness / interpretation caveats, **not correctness bugs**:
- **(med, fixable)** `target_R=0` (EOD-only) configs have a fat right-tail R; the survivor rule has no
  tail/median guard. The CL survivor is exactly this config (one +42.6R trade drives the mean).
- **(med, fixable)** `prior_atr`'s absolute gate, derived on the longer design window, can admit very
  few or ZERO holdout trades if the holdout regime is quieter — a power/interpretation risk for the
  ES survivor (reproduced n=0 on a low-vol slice).
- **(low, fixable)** the two-regime split is by trade count, not calendar midpoint — a weaker-than-
  implied regime test (chronological ordering itself is correct / shuffle-invariant).
- **(low)** no-slip EOD exit is mildly optimistic; `target_R=0` configs lean entirely on it.
- **(low, not fixable / inherent OHLC)** an entry-bar break-and-reverse that sweeps the stop intrabar
  on the entry bar survives to EOD — the MBP-1 tick verification is the correct mitigation (below).

---

## Verification stream 2 — MBP-1 tick fill verification

Re-checked each survivor's modeled trades against the Databento MBP-1 trade tape over the
design-overlap window 2025-05-01 .. 2025-06-09 (mechanics validation, NOT an edge read — this
overlap is a losing stretch for all three). Sealed holdout untouched.

| Symbol  | n checked | fill_rate | mean entry slip (tk) | stop-through rate | modeled net_R | verified net_R | verdict |
|---------|----------:|----------:|---------------------:|------------------:|--------------:|---------------:|---------|
| CL.c.0  |        26 |     1.000 |  -0.615 (conserv.)   |             1.000 |       -0.0051 |        +0.022  | HONEST (slightly conservative) |
| ES.c.0  |        23 |     1.000 |  +0.435 (median 0)   |             1.000 |       -0.1549 |        -0.1752 | HONEST, small gap-tail optimism (~0.02R) |
| RTY.c.0 |        28 |     1.000 |  -0.893 (conserv.)   |             1.000 |       -0.1823 |        -0.1716 | HONEST (slightly conservative) |

Across all three: every modeled entry trigger actually printed during the entry window
(fill_rate = 1.000, zero fantasy fills); every modeled stop exit had a real print THROUGH the stop
(stop_trade_through_rate = 1.000, no phantom stops); exit-reason classification matched the tape.
The bar-based fills are **not fantasy**. CL and RTY are slightly conservative (the model's +1-tick
adverse entry/stop assumption over-charges vs the tape). ES has the only optimism: median slip 0 and
fill_rate 1.0, but ~3 of 23 gap-through days add ~+0.02 R of under-modeled slippage-tail to the mean
— small, and on a sample the edge is not being read from. **No config's fills materially flatter the
edge.** This stream clears all three.

---

## Verification stream 3 — Robustness (block-bootstrap + stress)

Design window only (`_scratch/robust.py`); holdout untouched. Block-bootstrap over whole trading days.

| Symbol  | net_R   | boot CI (90%)        | P(edge>0) | worst year | yrs neg | entry-bar-include | 2-tick slip | robust |
|---------|--------:|----------------------|----------:|-----------:|--------:|-------------------|------------:|:------:|
| CL.c.0  | +0.0272 | [-0.0288, +0.0809]   |    0.766  | 2017 (-0.16) |     3 | +0.0272 (=base)   |   -0.0092   | **no** |
| ES.c.0  | +0.0858 | [+0.0111, +0.1617]   |    0.969  | 2018       |     3 | +0.0858 (=base)   |   +0.0631   | **YES** |
| RTY.c.0 | +0.0263 | [-0.0204, +0.0703]   |    0.834  | 2025 (-0.11) |     2 | +0.0263 (=base)   |   +0.0118   | **no** |

Entry-bar-skip is NOT load-bearing for any config: the entry-bar-INCLUDE variant produced net_R
IDENTICAL to baseline for all three (zero differing fills, incl. RTY's target_R=2). The stop sits a
full OR-width away and the target 2R away, so a single 1-minute breakout bar essentially never reaches
either bracket on the entry bar itself. One robustness worry removed across the board.

- **ES.c.0 — ROBUST.** P(edge>0)=0.969; 90% CI [+0.011, +0.162] clears zero; survives 2-tick slip
  (+0.063) and entry-bar-include (+0.086). Caveat: 3/8 negative years, edge concentrates in 2022/2024
  — but it passes every stress cleanly.
- **CL.c.0 — NOT ROBUST.** CI straddles zero, P=0.766, 3/10 down years, and it **flips negative under
  2-tick slip (-0.0092)** — one extra tick of cost erases the entire edge. Too fragile.
- **RTY.c.0 — NOT ROBUST.** Borderline: CI crosses zero, P=0.834, survives 2-tick slip only barely
  (+0.012). Disqualifier is **recency** — worst year is 2025 (-0.11), the most recent partial year
  immediately before the holdout boundary, i.e. the edge is decaying into the holdout window.

---

## Per-instrument GO / NO-GO

### ES.c.0 — **GO**
- Code review clean; no high-severity bug.
- MBP-1 fills honest (fill_rate 1.0, median slip 0, perfect reason agreement; ~0.02R gap-tail optimism
  only, on a non-edge sample).
- Robustness ROBUST: P(edge>0)=0.969, CI clears zero, survives 2-tick slip and entry-bar-include.
  Entry-bar convention is not load-bearing.
- **Condition for reading the result (must-fix below):** this is a `prior_atr`-gated config; if the
  holdout regime is quieter than design, the absolute gate (166.329 ticks) can admit very few or zero
  trades. **Before firing, and again when reading the result, check holdout n.** If n is small
  (roughly < 12, the MBP-1 floor used elsewhere) the holdout read is uninterpretable, not a PASS/FAIL.
  This is the one config to spend a holdout read on.

### CL.c.0 — **NO-GO**
- Code review clean and MBP-1 fills honest (slightly conservative) — both pass.
- **Robustness fails.** Edge is inside the bootstrap noise (CI [-0.029, +0.081] straddles zero,
  P=0.766) and **flips negative under a 2-tick slip (-0.0092)** — a single extra tick of cost erases
  it. Compounding this, it is the `target_R=0` tail-concentration config whose +0.027 design mean is
  driven by a single +42.6R trend-day trade, so the one holdout shot would be a high-variance lottery
  on whether a couple of big trend days land in the 12-month window. Do not burn the shot.

### RTY.c.0 — **NO-GO**
- Code review clean and MBP-1 fills honest (slightly conservative) — both pass.
- **Robustness fails.** Borderline overall (CI [-0.020, +0.070] crosses zero, P=0.834; survives
  2-tick slip only by +0.012), and the decisive disqualifier is **recency decay**: the worst calendar
  year is 2025 (-0.11), the most recent partial year directly abutting the holdout boundary. An edge
  decaying into the holdout window is not worth the single shot. Hold off.

---

## must_fix_before_holdout (ES only — fixable interpretation guards, not correctness bugs)

1. **Holdout-n guard for the ES prior_atr gate.** The absolute threshold (166.329 ticks) is derived
   on the design window; a quieter holdout regime can admit very few or zero trades. Before firing,
   confirm the gate admits a usable count, and when reading the result treat a tiny-n outcome
   (roughly n < 12) as INCONCLUSIVE rather than PASS/FAIL. (`orb_engine.py` prior_atr gate /
   `sweep.py` holdout shot.)
2. **Read the ES PASS with tail/median skepticism.** It is a `target_R=0` EOD-only config; the
   survivor rule has no tail/median guard. When reading the holdout, check whether net_R is
   outlier-driven (a few big trend days) vs median-positive across trades.

---

## Overall verdict

**Fire ONE holdout shot — ES.c.0 only (30m OR, target_R=0, prior_atr gate @ 166.329 ticks),** subject
to the holdout-n guard above (treat tiny-n as inconclusive, and read the PASS with tail/median
skepticism). **CL.c.0 and RTY.c.0 are NO-GO** — both pass code review and fill honesty but fail
robustness (CL flips negative on +1 tick of cost and is an outlier-driven target_R=0 config; RTY's
edge is decaying into the holdout window with a -0.11 worst year in 2025). The engine itself is clean
for look-ahead and fill honesty; the entry-bar-skip convention is not load-bearing for any candidate.

---

# RTY gap_fade verification

**Date:** 2026-06-20
**Candidate:** `RTY.c.0` / family `gap_fade` / params `g=0.5, s=0.75`.
Fade the RTH open back toward prior RTH close when the gap ≥ 0.5 ATR; stop 0.75 ATR; target = prior
close; else EOD-flat. Design net_R **+0.073** (n=420, ~52/yr), median **+0.108**, win **53.8%**,
net_R_ex_top2pct **+0.032**. Design window effective 2018-04-30 .. 2025-06-09 (RTY.c.0 bars start
2018-04-30). This is a *different* family from the ES/CL/RTY ORB candidates above (fade-at-open, not
breakout) and a structurally HEALTHIER shape than the spent ES ORB shot.

**Decision: CONDITIONAL** — GO on the code/fill/robustness merits; **DO NOT fire on the 2025-06-10 →
2026-06-09 window** because it was already partially consumed by HOLDOUT_LOG Shot #1 (ES vol-gated
ORB). Re-seal a fresh, never-read OOS window first; on that window this candidate is a fire.

## Stream 1 — Code review (look-ahead + fill honesty)

**Verdict: SAFE FOR HOLDOUT.** `look_ahead_clean = true`, `fill_honesty_clean = true`,
`safe_for_holdout = true`, `survivor_rule_correct = true`. No high-severity bug.

- **Look-ahead clean (probed on real RTY 2018–2025 data).** `prior_close` is the PRIOR RTH session's
  close via `.shift(1)` on date-grouped last-close (verified == prev-day close, ≠ same-day/future);
  ATR is prior-day day-range via `.shift(1).rolling(14)` (excludes today's range). `run_family` is
  PURE on its df (derives ATR/prior_close fresh in `_context`), so no design-period state leaks across
  the holdout boundary. The other four families (vwap_revert, afternoon_trend, pre_rth_break,
  gap_cont) were also verified causal.
- **Fill honesty clean (CLAUDE.md rule 8).** Entry = open ± 1 tick (taker, adverse); target =
  prior_close as a resting limit (no slip, correct for a fade); stop slips adverse (mean −1.01R,
  honestly worse than −1R); same-bar stop+target → conservative stop-wins; EOD flatten at the true
  15:59 RTH close (mods monotonic, 0/2215 violations, no DST duplicate-minute corruption). The
  at-the-open taker sidesteps the adverse-selection that killed `level_scalp_v0`.
- **Survivor rule correct.** `net_R_ex_top2pct` drops the top `ceil(2%)` by net_R and means the rest
  (rejects a synthetic spike shape); chronological half-split sorts by date first. Candidate
  reproduces EXACTLY (net_R +0.07327 == CSV), deterministic / byte-identical across two runs.
- **Three sub-high caveats, none correctness bugs:**
  - **(med, methodology — THE decisive one)** the day-flat families use `DESIGN_END='2025-06-09'`
    (`screen_families.py:30`), so the gap_fade sealed holdout is the **same** 2025-06-10 → 2026-06-09
    window that ES-ORB Shot #1 already read. The repo's own README (line 92) / HOLDOUT_LOG (line 50–51)
    state the 12-mo holdout is now partially seen and a fresh OOS scheme is required. gap_fade is
    mechanically unrelated to ORB (fade vs breakout) so contamination is low, but the window is no
    longer pristine. **User's discipline call — and the reason this is CONDITIONAL not GO.**
  - **(med, operational)** `run_family` derives ATR/prior_close FRESH and `simulate_trade` needs
    `min_periods=5` of run-up; running the holdout on a bare 2025-06-10+ slice silently drops the
    first ~3–5 trades (NaN ATR) → 58 vs 61 trades. **The holdout MUST be run on a df that includes
    ~25 trading days of run-up before 2025-06-10, then filter trades to `date >= 2025-06-10`.** Both
    variants are conservative (no look-ahead); they only differ in trade count.
  - **(low, inherent OHLC, mitigated)** `simulate_trade` manages from `ei+1`, skipping the 09:30 entry
    bar's own high/low. Quantified across all 420 design signals: 419/420 (99.8%) had NEITHER bracket
    reachable on the entry bar; the lone exception (2020-11-09 vaccine gap) was stop-only reachable =
    the skip was optimistic by exactly 1 trade (0.2%). Negligible; the MBP-1 tape check (forward from
    the real entry ts) is the correct mitigation and agreed 1.000.

## Stream 2 — MBP-1 tick fill verification

**Verdict: PASS (HONEST).** 9 candidate (g=0.5) entries checked against the Databento MBP-1 trade
tape; sealed holdout untouched.

| metric | value |
|---|---|
| n entries checked | 9 |
| entry fill_rate | 1.000 (zero fantasy fills) |
| mean entry slip | +0.000 ticks |
| exit-reason agreement | 1.000 (6 eod / 2 stop / 1 target) |
| modeled net_R (sample) | +0.1338 |
| verified net_R (sample) | +0.1342 |

Targets are resting limits at the prior RTH close — when price traded there the fill is real with no
slip (e.g. 2025-05-29 short filled exactly at target 2072.4). Stops fill where price actually traded
through; on 2025-05-08 the tape gapped a single tick through the stop, making the realistic fill if
anything slightly *conservative* vs the model's +1-tick-adverse assumption. No stop gapped >1 tick;
EOD exit = last print before 16:00 ET = the 1m close. `fill_confidence = exact`. The g=0.3
mechanics-only pass (n=12) reproduced identical behavior (fill 1.000, slip +0.000, agreement 1.000).
Fills do NOT flatter the edge.

## Stream 3 — Robustness (block-bootstrap + stress)

**Verdict: ROBUST.** Design window only; holdout untouched.

| metric | value |
|---|---|
| net_R | +0.0733 |
| bootstrap 90% CI | **[+0.0085, +0.1403]** (strictly positive) |
| P(edge>0) | **0.966** |
| median_R | +0.108 |
| net_R_ex_top2pct | +0.032 (NOT outlier-driven) |
| 2-tick slip | +0.0686 |
| entry-bar-INCLUDE | +0.0639 (edge does NOT depend on the entry-bar skip) |
| years negative | 2 of 8 (worst −0.0365) |
| 2025 (into boundary) | +0.234 (STRENGTHENING, opposite of the NO-GO ORB's recency decay) |
| param robustness | all 4 cells (g∈{0.3,0.5}×s∈{0.75,1.25}) net-positive AND median-positive — not a knife-edge |

The two read-guards that flagged the ES ORB NULL post-hoc (median, ex-top-k) BOTH pass here on the
design window: median +0.108, and the edge survives dropping the top 9 trades (+0.032). The critical
integrity check passes — including the 09:30 entry-bar range (conservative stop-wins) gives +0.064, so
the edge does not depend on the lenient entry-bar convention.

## Decision — CONDITIONAL

A GO on pure merit: **no high-severity look-ahead or fill bug, MBP-1 fills are not optimistic (verified
≈ modeled, +0.000 slip), and robustness clears every bar** (bootstrap CI strictly positive,
P(edge>0)=0.966, median-positive, ex-top-2% positive, 2-tick-slip robust, entry-bar-include robust,
4/4 params positive, no single-year dependence, strengthening into 2025). This is the median-positive /
tail-bounded shape the HOLDOUT_LOG v2 lesson asked for and is materially cleaner than the spent ES ORB
candidate.

**But it is CONDITIONAL, not GO, on one discipline blocker: the bar-only holdout window
(2025-06-10 → 2026-06-09) is no longer pristine** — ES-ORB Shot #1 already read it, and the repo's own
rule says a fresh OOS scheme is required. Firing the single shot on a partially-seen window would let a
PASS/FAIL masquerade as a clean OOS verdict, which violates the discipline that is this module's stated
durable asset. The contamination risk is LOW (gap_fade fade-at-open is mechanically unrelated to the
ORB breakout that touched this window), but "low" is not "zero," and a deployable claim cannot rest on
a spent holdout.

**Path to fire:** re-seal a fresh, never-read OOS window (e.g. extend the bars and seal the latest
unseen 12 months, or hold out an earlier never-screened block), keep `DESIGN_END` strictly before that
window, then fire this exact config (`RTY.c.0 gap_fade g=0.5 s=0.75`) ONCE on the fresh window with
the ~25-day run-up convention. On a pristine window this candidate is a GO.

## Read-guards (apply when the holdout IS read, on a fresh window)

1. **n guard.** Expect ~52 trades/yr → ~50–61 over 12 mo. If n < 15 the read is INCONCLUSIVE, not
   PASS/FAIL. Confirm the run-up convention was used (else the first ~3–5 trades drop to NaN ATR).
2. **Median guard (the ES-ORB lesson).** Require **median net_R > 0**, not just mean > 0. A positive
   mean with a negative median = outlier-carried = NULL (this is exactly how Shot #1 failed:
   mean +0.013 but median −0.359).
3. **Tail guard.** Require the mean to survive dropping the top ~2% (`net_R_ex_top2pct > 0`). If the
   edge collapses when the best few trades are removed, it is a trend-day lottery, not an edge.
4. **Shape guard.** Check the exit mix is balanced (design was 121 target / 95 stop / 204 eod), not
   dominated by a handful of large EOD trend-rides — the worst shape for a prop daily-loss limit.
5. **Cost guard.** Re-confirm the holdout result survives the +2-tick-slip stress (design +0.069).
6. **One-shot, log win-or-lose** in HOLDOUT_LOG.md; the shot is then SPENT for this config.
