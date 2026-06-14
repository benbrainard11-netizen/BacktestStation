# SPEC — prop_intraday_resolver_v0

This is the original design proposal, **rewritten and corrected against what the repo actually contains** (verified 2026-06-14 by a file:line grounding pass over `market_state/`, `risk_conditioner_v0`, `sizing_v1`, `prop_model_v0`, `backend/app/backtest`, `live_engine`, and `options_signals_v0`). Correction callouts are marked **⚠ CORRECTION** or **✓ CONFIRMED**.

The system name: **Mira-Resolver v1 — Intraday Hold/Break + Prop Governor.** Four layers.

---

## Layer 1 — Opportunity generator (objective intraday events)

Do not ask "should I buy or sell now?" Ask: *"at this pre-defined level touch, is the market more likely to hold, break, chop, or turn dangerous?"*

Fire on objective zone-touch events:

| Family | Examples |
|---|---|
| Prior levels | prior RTH high/low, prior full-day high/low, overnight high/low |
| Session levels | opening-range high/low, VWAP ± bands, session VWAP, session high/low so far |
| Volume levels | VPOC, HVN/LVN, volume-node edges |
| Gap / auction | gap midpoint, gap fill, prior settlement/close |
| Cross-index conflict | ES touching a level while NQ/YM/RTY disagree |
| Mira-style sweeps | sweep → reclaim/reject at an objective level |

**✓ CONFIRMED** this is exactly `market_state`'s locked architecture (`INTRADAY_SYSTEM.md:12-13`: *"detect zones → detect touch events → triple-barrier hold/break label → event-time microstructure features @ the touch → LightGBM → walk-forward OOS + ablation"*).

**⚠ CORRECTION — most of this is already built.**
- Level engine: `market_state/intraday/levels.py` builds PDH/PDL, overnight H/L, session open, opening-range H/L, prior-week close with correct ET segmentation and forward-knowledge guards (OR valid only after 09:45). 9 level columns today.
- Event scanner: `zone_events.py` (PDH/PDL, REAL, tested) and `events_v2.py` (vol-scaled, zones `[lo,hi]`, confluence counting, ES-only).
- **Net-new for Layer 1:** wire `levels.py`'s full set into the *scanner* (the baseline scanner only does PDH/PDL), then add gaps, VWAP, and VPOC as families. Each new family must **earn its seat** against the OFI baseline (Layer 2 judge) before it stays.

**✓ CONFIRMED** trade-frequency math: PDH/PDL-only already gives **~7 events/day** (`INTRADAY_SYSTEM.md:76`). Adding families clears "≥1 qualified opportunity/day" easily — but see binding constraint #2 in `PLAN.md`: ~7 events/day with day-clustering means the **day** is the independent unit (~25 independent OOS days), which is a thin sample, not a big one.

---

## Layer 2 — Resolver model (predict the event resolution)

Output a distribution, not a direction:
`P_hold, P_break, P_chop`, `P_target_before_stop`, `expected_R` + `q20/q50/q80`, `p_tail_loss` (`P(MAE_R>1R)`, `P(MAE_R>2R)`), `time_to_resolution`.

**Labeling (post-confirmation triple-barrier):** `t0` = first touch; `t1 = t0 + feature window` (100ms / 250ms / 1s / 2s); **features ≤ t1 only**; label measured **from t1 forward** (hold / break / chop / tail).

**✓ CONFIRMED** "outcome measured AFTER the OFI window" is the repo's sacred rule (`zone_events.py:42,144`; `events_v2.py:66`; `INTRADAY_SYSTEM.md:73`).

**⚠ HARD ADDITION — build-time lookahead assert.** The deployed Mira gate's edge turned out to be a **lookahead-selection artifact**: its 15 book-proxy features used a `[trig−30s, +60s)` window — they watched each trade's own first minute. Mask-test confirmed: without that peek, OOS expectancy was −0.05..−0.13 R. So Layer 2 must assert at build time that `t_feature_end ≤ t_decision` for every feature, every row. See `features.py::assert_no_lookahead`.

**Feature stack (start simple, earn complexity):**

| Group | Verdict in the design | **Repo-grounded verdict** |
|---|---|---|
| Event geometry | "useful, not the edge" | ✓ agree; already computed |
| Event-time MBP-1 (CKS OFI, top-book imbalance, spread, microprice, message rate) | "core" | ✓ **this is the baseline and the judge** (`zone_events.py:118-142`) |
| TBBO signed flow (aggressor vol, at-level vs through-level) | "core" | ⚠ signed-aggressor vol is *computed but never ablated standalone* (`zone_events.py:139`) — unproven, must earn its seat |
| MBO depth (cancel/add, queue depletion, iceberg, L2–L5) | "premium, overfit-prone" | ⚠ agree, and **thinner than stated** — see CORRECTION below |
| Cross-index (ES/NQ/YM/RTY, SMT, lead-lag) | "good conditioner" | ⚠ tested as *confirmation only*, never ablated as a clean feature group — **candidate, not proven** |
| Vol regime (RV, ATR, time of day) | "good conditioner" | ✓ free to add (`sync_regime` reuse), but must earn its seat |
| Options (net GEX, zero-gamma dist, wall dist, gamma sign) | "interaction only" | ✓✓ correct stance — see Layer-2 gamma note |
| Account state | "required for governor" | ✓ belongs in Layer 4, not the resolver's features |

**⚠ CORRECTION — MBO is much thinner than the design's "~124 days" implies.** Actual (2026-06-14): MBP-1 = **342 days** (2025-05-01..2026-06-09), TBBO = 315, but the **clean MBO trading-day cache is only 112 trading days, all in 2026** (2026-01-02..2026-06-09). Pre-2026 has *no clean MBO*. So MBO is a **5-month, single-regime ablated layer** — if it doesn't add OOS lift on that window it's decoration, and even if it does, regime-generalization risk is severe. Build the whole baseline on MBP-1/TBBO (13 months); treat MBO strictly as an ablation experiment.

**⚠ CORRECTION — gamma is interaction-only AND currently unvalidated.** The repo already **killed standalone GEX** ($75 EOD test, corr with next-day trendiness = −0.004, flat — `options_signals_v0/RESEARCH_AGENDA.md:45-53`). Good — the design agrees. But the *interaction* hasn't validated either: intraday pinning tests were **NULL** (`intraday_pin_step_b.py`). Wall-distance features exist (`fuhhhhh/features.py:44-46`: `opt_dist_zg/cw/pw`) and are reusable, but "wall-beyond-level / stop-hunt works" is **hypothetical** — keep gamma as a low-priority interaction term you must prove yourself, not an assumed-good conditioner.

**✓ CONFIRMED — the non-negotiable judge.** Baseline = **event-time OFI-only model**. The full system must beat it OOS or the extra families are decoration (`INTRADAY_SYSTEM.md:46-50`, implemented in `hold_break_model.py` via day-block bootstrap delta-CIs). This is the law. `resolver.py::ofi_only_baseline` and `resolver.py::judge` reuse it.

**✓ CONFIRMED — LightGBM first, no transformer.** Tabular LightGBM/CatBoost + isotonic/Platt calibration per walk-forward fold. Sequence/TSFM only later, as a *feature generator* after the tabular baseline is beaten. The repo's sample is too short in microstructure-regime space for a big TSFM.

**⚠ DEFER — mixture-of-experts.** The 4-expert (ES / NQ / high-vol / low-vol) MoE is premature. One resolver must prove OOS lift first. With ~7 events/day × ~25 independent OOS days and an 8-group feature stack, you are squarely in the overfit zone the repo already learned about ("4 mirages already" in ~2k events — `mira_upgraded_v0/combine_model.py:4`). Ablate family-by-family; let the day-block bootstrap CI be the gate.

---

## Layer 3 — Risk conditioner (protect the edge, don't over-filter it)

Given a *valid* candidate, output a size multiplier in `{0.0, 0.25, 0.5, 0.75, 1.0}`. It does **not** create trades, flip direction, or size above 1.0.

**✓ CONFIRMED — this is `risk_conditioner_v0`'s locked contract verbatim** (`PLAN.md §1,§5`; `MODEL_CARD.md`). It predicts `p_bad, p_tail, pred_MAE_R_q80/q95, p_target_before_stop, time_in_trade` and maps to a multiplier.

**✓ CONFIRMED — do NOT pool Type A and Type B.** Hard rule from `risk_conditioner_v0/PLAN.md §4`: separate heads/objectives; Type B may only reduce tail risk, never produce a generic good/bad score.

**⚠ STATUS — risk_conditioner_v0 is PARKED and mostly stubs.** Parked 2026-05-27 (Ben doubted Type B label durability — OB/FVG "too retail-known"). `build_features.py`, `build_labels.py`, `integration.py`, `evaluation.py` are all stubs. What's real and reusable: the 45-feature schema, walk-forward/embargo spec, the Type A/B head architecture, and the **iter-0 MBO validation** (`cancel_rate_60s` has a real 5× decile lift on forward absolute moves). This project should build the **Type A path first** (less controversial than Type B) and reuse the schema.

---

## Layer 4 — Prop-firm governor

Convert signal quality + account state into a final, firm-compliant size. If the account is fragile: require higher edge, cut size, stop after first loss, avoid correlated simultaneous trades. If healthy and edge is strong: normal size. If `p_tail` high: skip or quarter-size.

**✓ CONFIRMED — almost all of this exists and already optimizes the right objective.** `sizing_v1` + `prop_model_v0`:
- Account state machine with hard daily-loss-limit stop and trailing-DD floor lock (`account.py`, `firm_rules.py:136-146`).
- `sizing.py::size_position` with `vol_targeted` (ATR + conviction + DD-buffer + balance) — the right sizing lever.
- `risk_manager.py::decide` — threshold + direction-asymmetry + news-blackout + account gates.
- 6 firms audited (Topstep, Apex, MFFU, Ludic, Tradeify, TPT) in `config/firms/*.yaml` + `funnel_specs.py`.
- `eval_ev.py` — Monte-Carlo eval-EV (P(pass) × funded value − cost), sweeps edge levels per firm.
- `fleet_sim.py`, `monte_carlo_milkability.py` — correlated multi-account + block-bootstrap survival sims.

**✓ CONFIRMED — the repo already optimizes survival/pass-rate, not Sharpe or win-rate** (`sizing_v1/README.md:88-95`: *"Pass rate is what matters. Not Sharpe. Not AUC. Pass rate."*). So the design's "brutal truth #1" (win rate isn't the goal) is preaching to a stack that already does this. **Win rate is a diagnostic only.**

**⚠ REAL GAP the design misses — intraday bar-grain MTM.** `account.py` checks breaches only at *trade close*. An intraday DLL breach (−$1k at 11am, recovers to −$400 by close) is invisible today, so the governor would over-report survival. A prop governor MUST mark-to-market within the day. This is the most important net-new piece in Layer 4.

---

## Architecture (data flow)

```
clean Databento (read_*_trading_day) / walls parquet
        ↓
event scanner            ← reuse market_state/intraday/levels.py + zone_events.py
        ↓
event-time feature builder  ← reuse zone_events CKS OFI; assert_no_lookahead
        ↓
resolver (multi-head LightGBM)  ← reuse hold_break_model.py harness + judge
        ↓
OFI-only baseline judge (NON-NEGOTIABLE)
        ↓
risk conditioner (size_mult)  ← reuse risk_conditioner_v0 schema/contract
        ↓
prop-firm governor (account-safe size)  ← reuse sizing_v1 + prop_model_v0
        ↓
deterministic backtest + tick-replay fills + Monte Carlo  ← reuse backend/app/backtest
```

## Row schema (one row per touch event)

```
event_id, symbol, session_date, t_touch, t_feature_end,
level_family, level_price, side_candidate, branch_candidate
features:  geometry.* | mbp1_event_time.* | tbbo_signed.* | mbo_depth.* |
           cross_asset.* | vol_regime.* | options_context.* | (account_state lives in Layer 4)
labels:    y_hold, y_break, y_chop, y_target_before_stop,
           realized_R, MAE_R, MFE_R, time_to_target, y_tail
```

## Scorecard (the model is "real" only if all hold)

| Metric | Requirement |
|---|---|
| OOS expectancy | positive after fees + slippage |
| Beats judge | strictly beats event-time **OFI-only** model OOS (day-block bootstrap CI) |
| Win rate | diagnostic only (≥52% nice, never traded for) |
| Avg win / avg loss | must support the win rate |
| Trades/day | median ≥ 1 *qualified* opportunity/day across selected symbols |
| Daily-loss tail | p95 daily loss reduced vs ungoverned |
| Drawdown | lower than ungoverned |
| Calibration | predicted-60% bucket wins ≈ 60% |
| Robustness | holds across folds, not one lucky month |
| Ablation | every feature family earns its seat vs the OFI baseline |
| Prop sim | improves **pass / reward probability**, not just Sharpe |

## Build first (concrete v0)

Symbols ES, NQ first → then YM, RTY. Events: prior RTH H/L, overnight H/L, OR H/L, VWAP±bands; gaps + VPOC only after base passes. Features: geometry + MBP-1 OFI (100ms/250ms/1s/2s) + TBBO signed vol + top-book imbalance + spread/microprice + RV/time + cross-index relative move. Labels: hold/break/chop + target-before-stop + realized_R + MAE_R + time-to-resolution. Models: LightGBM multiclass (branch) + binary (target-before-stop) + quantile (MAE_R / expected_R), isotonic calibration per fold. Governor: prop-firm-sim objective = maximize P(reach target) subject to DLL / DD / consistency. **Only after that passes:** MBO depth layer → options/GEX interaction → sequence embeddings → MoE.
