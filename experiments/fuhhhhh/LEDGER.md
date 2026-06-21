# LEDGER — every test gets an entry (SPEC rule 12)

Format: id | what | window/n | result | verdict | diagnosis/notes. Verdicts lock after
one revision cycle. Negative results must name the failing component.

## Phase 0 — data sanity + inherited-artifact lookahead audit (2026-06-12)

**P0.1 — phase0_sanity.py run.** PASS.
All artifacts present. Joint intraday-options × MBP-1 window = 271 days
(2025-05-02 → 2026-06-05); dev = 229 days, sealed holdout = 42 days. Probe day
2026-03-31 10:00 ET: SPX 6450.5, ES 6495.50, basis +45.03 (sane). Deep backfill
still running (0/3 spx shards) — fine for phases 0–2.

**P0.2 — `intraday_gex.py` (per-minute GEX panel) lookahead audit.** PASS (rule 2).
Line 108–111: chain for day D = most recent EOD chain **strictly before** D
(`bisect_left − 1`, skip if none — that's why the panel starts 05-02 not 05-01).
T-1 OI/IV repriced at live spot. Notes:
  - `call_wall`/`put_wall` are unconstrained argmax/argmin of per-strike net dealer
    gamma — **either side of spot** (probe day had call wall below spot, put wall
    above). Objective engine must select "nearest level above/below" itself, never
    assume side.
  - `zero_gamma` is NaN when cumulative profile never crosses 0 (known: flip exists
    only ~46% of days). Treat as optional level, not a required feature.
  - EOD IV held flat intraday = stale-but-legal approximation; on cache gaps the
    chain may be >1 day stale (still causal).

**P0.3 — `pull_0dte.py` (0DTE flow panel: net gamma/vanna/charm) lookahead audit.** PASS.
Per-minute rows use that minute's IV/underlying and **cumulative volume ≤ t**
(sorted cumsum, line 81–82). Causally clean. Caveat: dealer-sign = right-type proxy
(calls +, puts −) — a positioning *proxy*, so SPEC rule 4 sign-convention battery
applies to anything built on `net_gex` sign.

**P0.4 — `spot_lean.py` (intraday spot) lookahead audit.** PASS.
Strike *selection* uses day D's own EOD index close, but selection only chooses which
contract to read — `underlying_price` is the true contemporaneous spot regardless of
strike (documented in the script). No value contamination.

**P0.5 — `iv_features.py` (intraday ATM IV / skew) lookahead audit.** PASS.
Per-minute ATM/wing IVs from the same minute's chain rows; contemporaneous; 5-min grain.

**Phase 0 exit gate: MET (2026-06-12).** Coverage table in DATA.md; all four inherited
artifacts have PASS notes above.

## Phase 1 — full system v0, built + run (2026-06-12)

**P1.1 — pipeline built end to end** (data_io / features / objectives_labels /
build_dataset / model_v0). Dataset: 13,319 rows / 219 dev days, classes dn/up/neither =
5,526/5,623/2,078, ambiguous 92 (kept, scored as stops). Adversarial review (independent
agent): **no critical lookahead**; findings F1 (ambiguous-row exclusion), F2 (Sunday
overnight partition), F3 (entry at pre-decision close), F4/F5 fixed before reading
results; F6–F10 logged as accepted v0 approximations in the review record.

**P1.2 — v0 walk-forward results (dev OOS, EV rule ≥ +0.05R, net of 0.576 pts costs):**

| ablation | n | meanR | CI90 | logloss |
|---|---|---|---|---|
| geometry floor | 2,927 | −0.137 | [−0.204,−0.114] | 0.7951 |
| futures+geo | 3,424 | **−0.088** | [−0.156,−0.070] | **0.7814** |
| options+geo | 3,551 | −0.120 | [−0.178,−0.072] | 0.8353 |
| combined | 3,535 | −0.113 | [−0.187,−0.094] | 0.7995 |
| shuffled-target control | 4,950 | −0.258 | — | (healthy: clearly negative; FAIL only if positive) |

**Diagnosis (rule 12 — component-level, not a verdict):**
- Machinery is honest: control strongly negative (= cost drag, as the race-geometry
  math predicts: any race is ~zero-EV gross, so uninformed selection nets −costs).
- **Futures block carries real signal**: beats the geometry floor by +0.049R and has
  the best logloss — but not yet enough to clear ~0.08–0.12R cost drag.
- **Options block v0 is noise-dominated at this grain**: options+geo logloss WORSE than
  geometry alone (0.8353 vs 0.7951) → current opt_ features (panel levels + flow
  deltas as flat additives) dilute rather than inform. Failing component = options
  FEATURE ENCODING, not necessarily the options thesis — interactions/conditioning
  untried, order-flow confirmation stage not built yet.
- Top features: geo distances, fut_rv_30m, fut_dist_onh, opt_atm_iv, opt_dist_zg.

**Iteration-1 growth list (registered, reordered per Ben/GPT-5.5 steering 2026-06-12):**
(1) timeout leg in EV + re-lock baseline; (2) MBP-1 order-flow block vs the
futures+geometry champion (options quarantined); (3) calibration + EV threshold;
(4) wall-zone/options interactions. Judged on ranking, not just mean R.

## Iteration 1 — order-flow confirmation increment (2026-06-12)

**P2.1 — exact changes.** EV rule gains the timeout leg (p_none × train-only E[gross
r|timeout], per fold — eval_lib.py); mbp_ block: 31 tightly-scoped MBP-1 features
(top-of-book imbalance, Cont OFI, aggressive flow, price/flow divergence,
spread/intensity, objective-relative interactions; depth-replenishment + cross-day
tod-normalization deliberately skipped). Labels/objectives/splits/costs/holdout
UNTOUCHED (manifest class counts byte-identical: 5526/5623/2078/92). Parallel
delayed-entry outcome columns added (y_d1, r_*_d1). Adversarial review of the feature
engine: NO critical lookahead; fixed M1 (same-ns event ordering → lexsort on
(ts_event, sequence) — mirror's unstable sort made OFI path-dependent), L1/L3/L6.

**P2.2 — timeout-patched baseline (same EV_MIN=0.05).** geometry −0.137→−0.113;
champion B futures+geo −0.088→−0.088 (gross +0.003, ll 0.7814); options −0.120→−0.116
(ll 0.8353, still worst — quarantine justified).

**P2.3 — results (dev OOS, net of costs):**

| ablation | n | meanR | gross | logloss | Brier |
|---|---|---|---|---|---|
| A geometry | 3,660 | −0.113 | −0.017 | 0.7951 | 0.4674 |
| B futures+geo [champion] | 3,923 | −0.088 | +0.003 | 0.7814 | 0.4591 |
| C mbp+geo | 3,611 | −0.125 | −0.038 | **0.7722** | 0.4598 |
| D fut+geo+mbp [candidate] | 3,809 | −0.097 | −0.009 | **0.7711** | **0.4568** |
| E options+geo [diag] | 3,978 | −0.116 | −0.016 | 0.8353 | 0.4841 |
| F all [diag] | 3,926 | −0.109 | −0.017 | 0.7912 | 0.4670 |

Controls: G shuffled-target −0.251 (healthy). **H day-shuffled MBP: ll 0.7830 ≈
champion's 0.7814 (vs candidate 0.7711)** → the prediction lift is genuinely from
ALIGNED same-day order flow; attribution clean. I delayed-entry (1m): candidate
degrades LESS than champion (−0.025 vs −0.045) → flow info persists ≥1m.
Ranking: B spearman +0.36, D +0.26; BOTH top EV deciles negative (B −0.086, D −0.229)
— extreme-EV rows are geometric long shots where probability error × payoff ratio =
adverse selection. Info-vs-geometry diagnostic (diag_info_edge.py): |p_dir − geometric
prior| deciles have NO positive cell; best cells ≈ −0.05 net ≈ +0.04 gross vs ~0.09R
avg cost drag. Every month negative for every ablation.

**P2.4 — verdict per acceptance criteria.** MBP improved PREDICTION (logloss/Brier,
clean attribution, better delay robustness) but NOT net R, NOT top-decile EV, NOT
months+. Per the pre-registered failure list the failing components are:
"MBP features predictive but not after costs" + "cost drag too large / trade frequency
too high" + EV tail adverse selection. NOT "MBP not predictive" — do not drop the block.

**P2.5 — next recommended increment (#2, economics/selectivity):** the construction
races to objectives a median ~5–8 pts away → cost 0.576 pts ≈ 0.09–0.12R per trade,
larger than any information edge found. Attack the economics, not the feature count:
(a) raise the objective-distance floor (registered param change → dataset v2, baseline
re-locked, labels regenerated — allowed outside Iteration 1's freeze); (b) per-fold
isotonic calibration before EV; (c) EV_MIN sweep as registered secondary; (d) cap/
shrink extreme payoff ratios in EV (tail fix). Success bar: a selective cell (top EV
decile or dev-decile) goes POSITIVE net with multi-month consistency.

## Iteration 2A — decision economics on FROZEN v1 labels (2026-06-12)

**P3.1 — what ran.** Nested per-fold calibration (none/isotonic/sigmoid; calibrator +
EV_MIN chosen on each fold's last-21-train-days segment, never on test), payoff-ratio
caps {uncap, 1.5, 2, 3, 4} (selection-side only), nested EV_MIN grid {0–0.20}.
Labels/objectives/features/splits/costs/holdout untouched. Code: calib_lib.py,
model_v2a.py, check_top_cells.py; full matrix in out/report_v2a.md.

**P3.2 — results.** Calibration is real: D logloss 0.8055 raw → 0.7202 (sigmoid) /
0.7345 (isotonic). The EV-tail crash is FIXED by cap+calibration: top deciles went
from worst to best. Best threshold cell: D isotonic/cap1.5 **−0.036 net / +0.030
gross, PF 0.90, DD −93** (vs champion −0.088). Top-quantile cells went positive:
D top5% +0.015 (n=313), D top2% +0.040, B top2% +0.061.

**P3.3 — minimum-sample battery on the positive cells: ALL FAIL.** B top2%: fold 4
alone (+0.905) carries it; drop-best-5-days → −0.149; top-3 days = 2.3× total profit.
D top5% (the most honest: folds+ 3/5, gross +0.085): drop-best-5 → −0.047 AND 1-min
delay → −0.051 (both sign flips). D top2%: same flips. Controls healthy (G −0.122
through the full nested pipeline; H ll falls back to champion level).

**P3.4 — 2A gate verdict: NO stable positive selective cell on v1 labels.** Decision-
layer fixes are necessary but not sufficient → proceed to 2B (pre-registered).

## Iteration 2B — dataset v2 economic objective filters (2026-06-12)

**P4.1 — datasets (pre-registered grid, nothing else tried).** Both with objective cap
1.0 ATR, both sides ≥ floor; floor from cost_to_objective cap: v2_c006 (cap 0.06 →
9.6 pts) and v2_c004 (cap 0.04 → 14.4 pts). 45-min barrier and all other label params
frozen. Builder now records cost-burden + mins_to_resolve columns; dataset_v0 artifact
protected. Effect: median race distance 5–8 pts → 16/22 pts; median cost burden 0.10R
→ 0.035/0.026R; **timeout rate 15.6% → 66.7%/80.7%** (the 45-min barrier is now the
binding constraint). MBP caches rebuilt per dataset; objective-relative interactions
recomputed against v2 objectives. Decision layer carried from 2A (isotonic/cap1.5,
nested EV_MIN; cap variants reported unhidden).

**P4.2 — re-locked tables (net R | gross | logloss).**
v2_c006: A −0.062|−0.030|0.920 · B −0.039|−0.005|0.904 · C −0.005|+0.029|0.878 ·
**D +0.016|+0.053|0.897 (n=920, PF 1.05, mo+ 4/6, CI [−0.004,+0.156])** ·
E +0.012 · F +0.036 (diag; options inside).
v2_c004: A +0.015 · B −0.059 · C −0.012 · D −0.018 (but D cap-None +0.034, mo+ 5/6) ·
E +0.023 · F +0.017. Feature ladder on c006 is finally right: geo < fut < mbp < combined.

**P4.3 — controls + drift autopsy.** G(c006) −0.030 healthy; **G(c004) +0.007 — first
positive control reading** → triggered a drift autopsy (diag_drift.py): always-long
over ALL rows is NEGATIVE on both datasets (−0.053/−0.035), candidate c006 trades are
45% long/55% short with shorts carrying profit (+0.036 vs longs −0.008), and
model-vs-same-rows-always-long delta = **+0.097 (c006) / +0.032 (c004)** → the
positive cells are SIDE-PICKING SKILL, not drift; G(c004)'s +0.007 = noise (n=2116,
within CI of 0). H (day-shuffled MBP) on c006: +0.008 — between B and D, so MBP
trade-level attribution on v2 is NOT established (its logloss attribution is).
Delayed entry: D c006 −0.001 (survives, barely); drop-best-5: −0.030 (FLIPS — day
concentration persists). Fold spearman ≈ 0 everywhere (within-set ranking weak; the
lift is universe+side selection, not fine ranking).

**P4.4 — verdict vs pre-registered success criteria.** First positive-net candidate
cell in the program (D c006 +0.016, n=920, real counterfactual skill, survives delay,
gross +0.053) — but it FAILS the stability bar: folds+ 2/5, drop-best-5 flips sign.
**No victory declared.** Trajectory across constructions: v1 −0.088 → 2A −0.036 →
2B +0.016 net (gross −0.017 → +0.030 → +0.053), failure mode narrowed to
day-concentration + weak within-set ranking + timeout dominance.

**P4.5 — recommended Iteration 3 (in order):**
1. **Horizon fix** (single pre-registered change): 45-min barrier vs 16–22-pt
   objectives mismatch drives 67–81% timeouts; test 90-min barrier on v2_c006 specs.
2. **Prop risk shell as day-concentration treatment**: max trades/day + daily stop +
   top-K-by-edge-per-day selection (caps clustering structurally, and it's the
   phase-4 prop layer arriving early for a reason).
3. **Options un-quarantine as CONDITIONAL interactions on v2 labels**: E (+0.012/
   +0.023) and F (best c006 cell +0.036) hint options matter at longer horizons —
   exactly the original thesis. Wall-zone × flow interactions per the v0 plan.
4. MBP trade-level attribution re-test after 1–3 (H control must separate D from B).

## Iteration 3 — REDESIGN to event-triggered seek-the-wall (Ben's mental model, 2026-06-12)

**P5.0 — why redesigned.** Ben clarified the actual idea: not a symmetric timed race —
a **trigger fires (sweep / SMT / order-flow shift) → price travels to an options WALL →
open horizon until EOD**, stop = adverse ATR move. Options = the WHERE (target), triggers
= the WHEN. This is his Mira/upgraded_mira machinery aimed at the options walls (that
family already showed +0.5–0.8R toward gap/OR levels w/ honest fills; walls are the new
target). He asked to test each trigger separately AND in confluence. New modules
(v0/v1/v2 pipeline untouched): triggers.py, build_events.py, event_study.py.

**P5.1 — construction.** Triggers, all causal (adversarial review: NO critical
lookahead; SMT fractal pivots correctly gated to p<=idx-K; fixes F6/F8/F10 applied; F7
same-bar fills = 2.2%, immaterial). Sweep = poke beyond 35-bar reference extreme +
reclaim; SMT = ES/NQ swing divergence (NQ as confirm index); flow = MBP signed-vol
|z|>=1 toward a side. Target = nearest gamma wall in trigger direction within
[2pts, 2*ATR]; stop = STOP_ATR*ATR; label = first-passage to EOD (reuses race_label/
realized_r). 3,441 events / 219 days (~16/day); sweep 1455 / smt 895 / flow 1436.

**P5.2 — event study (raw triggers, no model yet).** Two stop widths:
- The pooled "edge = reach - geom_prior" was -21 at 0.5 ATR but that's a TIMEOUT
  artifact (46% never resolve vs prior assumes all resolve). At 0.25 ATR timeouts drop
  to 31%; resolved-reach ~ geom prior (no clear magnet effect either way).
- **Fade check is the real tell**: post-trigger stop-hit rate 13% vs 38% random (0.5
  ATR) - price does NOT run hard against the trigger. Faint directional lean is real.
- Pooled meanR ~ -0.02 to -0.03 (cost-bound, as the whole repo's history predicts).
- **Component breakdown**: SWEEP carries; SMT weakest; FLOW wants a WIDE stop
  (momentum needs room); **confluence HURTS** (-0.10, stacking selects chaos);
  **SHORT side >> long** everywhere (consistent since 2B).

**P5.3 — standout cell: sweep-solo SHORT (tight 0.25-ATR stop).** n=516, meanR **+0.101
net / +0.134 gross**, reach 42%. Stability battery (the bar that killed every prior
cell): **drop-best-5-days +0.029 (STAYS POSITIVE - a program first)**, drop-both-5
+0.085, **delayed-entry +0.049 (no degradation)**, months+ 6/11. Wide-stop version
+0.047 net, same robustness shape. Honest tells: (a) post-hoc slice (sweep&solo&short)
- multiple-comparison risk; (b) TIME-DEPENDENT - Jul-Nov 2025 negative, Dec 2025-Mar
2026 strongly positive (regime or recent-window-is-where-it's-real); (c) top-3 days =
~52% of total; (d) not yet through a selection model, tick fills, or holdout.

**P5.4 — verdict.** Best pulse the program has produced and the first to survive
drop-best-days + delayed entry - but NOT victory (post-hoc slice, time-concentrated,
unverified at tick grain). Trajectory: v1 -0.088 -> 2A -0.036 -> 2B +0.016 ->
**v3 sweep-short cell +0.10 net (robustness-surviving)**.

**P5.5 — recommended Iteration 4 (in order):**
1. **Selection model on the events** — THIS is where options come in as the FILTER:
   LightGBM over the event set (sweep + short biased) using opt_/mbp_/fut_ features to
   rank which triggers will reach the wall; nested calibration + full control battery.
   Does options context lift the sweep-short cell?
2. **Tick-grain fill verification** (mira_upgraded_v0/fill_realism.py) on the
   sweep-short cell before any R is believed as money (CLAUDE rule 6 / review F7).
3. **Regime split** — is the time-dependence a tradable regime (down/vol days) or just
   the recent window? Condition on realized-vol / trend state.
4. Only after 1-3 hold: a single, logged read of the sealed holdout.

## Iteration 3.1 — TYPED multi-TF triggers (answers "how are we classifying sweeps", 2026-06-12)

**P6.0 — why.** Ben pushed: the sweep detector was one blind rolling-window definition
(no level-type / TF / proximity / overshoot / confirmation awareness). Redesigned sweeps
into a TAGGED event family (typed_triggers.py, build_events_typed.py → events_v3t,
10,934 events) so the DATA classifies which sweeps work. Level menu = session levels
(PDH/PDL/ONH/ONL/OR) + multi-TF swing pivots (5/15/60m). Tags: swept_type, swept_tf,
swept_dist_atr, overshoot_tk, confirm_1m/5m/15m, n_levels_swept. SMT made multi-TF +
TF-tagged. Ben's choices: session+multi-TF menu; tag 1m/5m/15m confirmation, data decides.

**P6.1 — VALID sweep findings (adversarial review: sweep/levels/labels causally CLEAN,
no lookahead).** Sweeps classify cleanly and the answer is mechanistic:
- **TIMEFRAME: 5m (local) sweeps win** (+0.003 solo, gross +0.020, 7/11 mo); 15m/60m/
  OR/ON/1D sweeps all LOSE (−0.03 to −0.20). Big structural-level sweeps underperform.
- **OVERSHOOT: shallow wins, deep loses** — 2–8 ticks past the level = +0.01 (7/11 mo);
  >8 ticks = −0.07 (3/11 mo). A shallow poke (near the extreme) reaches the wall; a deep
  violent poke is a real breakout, not a sweep. (Directly validates Ben's "sometimes it
  doesn't sweep the absolute extreme but near it" intuition.)
- **SIDE: short >> long** (5m shallow SHORT +0.054; LONG −0.054).
- **Headline cell, SMT-independent** (5m sweep, overshoot≤8, SHORT, ~fired_flow): n=461,
  meanR **+0.039 / gross +0.057, 7/11 months**, drop-best-5 −0.007 (~flat), delayed
  +0.038. Robust to the SMT bug below.
- PROXIMITY tag uninformative (sweeps are ~all 0–0.25 ATR by construction — price must
  be AT the level to sweep it).

**P6.2 — SMT findings RETRACTED (CRITICAL data-integrity bug, NOT lookahead).** Review
found `_smt_one` compares ES vs NQ resampled candles aligned by INTEGER INDEX, but NQ's
overnight frame was built asymmetrically (full prior-day partition vs ES's windowed
overnight) and build_tf_swings strips the date (ms-of-day only) → ES candle[i] and NQ
candle[i] are hours/days apart on every day. So fired_smt/smt_tf = noise; the "60m SMT
+0.036" result is INVALID. Not a future-leak (the ≤t_ms filter still excludes future
candles) — a wrong-pairing bug. **Cannot answer "what candle SMT works with" until fixed.**

**P6.3 — confirm_5m/15m flags DEGENERATE.** detect_sweep only emits when price>level, so
confirm_1m is true by construction and 5m/15m collapse to ~always-true. The "5/15m
confirmation" question is also unanswered until reworked (need higher-TF candle CLOSE vs
level, not high/low; build_tf_swings must also agg close).

**P6.4 — verdict.** Sweep classification = a real, mechanistic win (5m + shallow + short),
robust and lookahead-clean. SMT + confirmation = not yet answered (bugs found, fixes
specified). Next (Iteration 4, reordered): (a) FIX SMT — symmetric NQ overnight loader +
align ES/NQ by absolute timestamp + start-array-equality assert; rework confirm flags;
rebuild events; (b) tighter-stop typed events; (c) selection model using the sweep tags
(swept_tf/overshoot) + opt_/mbp_/fut_ as features = options come in as the filter;
(d) tick-fill verification; (e) then holdout.

## Iteration 3.1-fixed — SMT alignment + confirmation reworked (2026-06-12)

**P6.5 — fixes applied.** (1) NQ overnight now loaded SYMMETRICALLY to ES
(overnight_bars gained a root param). (2) typed_triggers rewritten: candles keyed on
ABSOLUTE epoch-ns, NQ reindexed onto ES's bin grid, SMT compares ES vs NQ at the same
timestamp with a build-time start-array-equality assert. (3) confirmation reworked to
the last completed higher-TF candle CLOSE vs level (build_tf_swings now aggs close);
degenerate confirm_1m dropped. Rebuilt events_v3t: SMT events 7,573 → 2,954 (the broken
version fired on noise); sweeps unchanged (4,796) — confirms sweeps were never affected.

**P6.6 — CORRECTED answers (the fix flipped the SMT verdict).**
- **SMT: the real cell is 15m SMT SHORT** (+0.048 net / +0.065 gross, n=393, 7/11 mo,
  survives delay +0.050) — but day-concentrated (drop-best-5 → −0.090). The earlier
  "60m SMT +0.036" was a pure artifact of the misalignment; corrected, 60m SMT is the
  WORST (−0.095). Lesson logged: a broken cross-asset alignment gave a confidently
  wrong TF answer — the assert now prevents recurrence.
- **Confirmation: 15m confirmation HELPS** (sweep-short −0.039→−0.024; 5/11 vs 3/11 mo).
  5m confirm still ~always-true (non-discriminating). Validates Ben's 15m-confirmation
  intuition. 5m-sweep-SHORT + 15m-confirm = +0.026 (6/11 mo, delay +0.027).
- **Sweeps unchanged & confirmed**: 5m local + short carries (+0.014, gross +0.030);
  big-TF/ON/1D sweeps lose; deep (>8tk) pokes worst. (P6.1 stands.)

**P6.7 — honest state.** Two mildly-positive, delay-surviving cells (5m-sweep-short
+15m-confirm; 15m-SMT-short) — both still dip negative on drop-best-5-days. Day
concentration is the persistent weakness across the whole program. All trigger
questions now answered with VALID, lookahead-clean code. → Iteration 4 unchanged
(selection model = options as filter; then tick fills; then holdout); the selection
model + a top-K-per-day rule is the designed treatment for the day-concentration weakness.

## Long-history feasibility study (Ben: "one asset / not a long time — how accurate?")

**P7.1 — why.** Dev window is ~11 months / 1 asset because that's all the INTRADAY SPX
options data there is (vendor floor 2025-05; the running 2017+ backfill is EOD-only and
won't extend intraday). To address "not a long time", explored using deep EOD walls
(2019+) as intraday TARGETS over a 6.5-year ES history (triggers are bar-based, work
full history; MBP-1 order flow only 2025-05+).

**P7.2 — accuracy measured (diag_longhist_accuracy / walls_v2 / dumps).**
- BASIS (SPX→ES) mapping with a prior-day basis: ACCURATE — |error| median 1.5pt, p95
  4.5pt vs ~19pt target; only 3-4% of days >10pt (rolls/COVID). Non-issue.
- WALLS: the stored walls_deep uses a max-GEX-per-side definition ≠ the intraday panel's
  signed-net-gamma argmax/argmin. Rebuilt walls_v2 (build_walls_v2.py) with the
  intraday-consistent definition + ≤30 DTE, cache-only, 1,263 days 2019-2026 (2021-22
  gap still backfilling). VALIDATION (vs intraday panel, correct day pairing): **call_wall
  reconstructs OK (all defs ~agree, tens of pts); put_wall does NOT (~60pt median error,
  bigger than the target).** Dumps show the put_wall is INHERENTLY unstable — single
  most-negative-gamma strike jumps with OI; even the live intraday put_wall drifts ~400pt
  WITHIN a day (e.g. 2025-08-28 open 6400 → close 6000). Not a reconstruction bug, a
  property of the quantity.

**P7.3 — verdict: long-history OPTIONS-WALL test is NOT trustworthy on the short side.**
Our edge is short → target = downside/put wall → exactly the unstable, unreproducible
quantity. Building a 6.5-yr backtest on it = building on sand (same trap as the SMT bug,
caught pre-build). walls_v2 kept as an artifact (call_wall side is usable; auto-extends
as backfill fills 2021-22) but NOT used as the short-side long-history target.

**P7.4 — honest scope going forward.**
- The RICH-options-features test is fundamentally ~11-month / 1-asset bound. Accept it;
  lean on walk-forward + the full control battery + the small-sample caveat. This is
  where the selection model (options as filter) runs.
- For long-history ROBUSTNESS of the TRIGGER half (the across-regimes question), test
  sweeps/SMT → well-defined SESSION/SWING levels (perfectly defined 2019+), NOT options
  walls. Tells us if the trigger machinery generalizes across regimes; options-as-target
  stays 11-month. (Consistent with upgraded_mira already showing the trigger family
  generalizes across ES/NQ/YM/RTY.)
- Cross-asset options-walls (NQ via self-computed NDX walls) remains a separate
  data project, deprioritized.
