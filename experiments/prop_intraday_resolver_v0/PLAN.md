# PLAN — prop_intraday_resolver_v0

Phased build order. Each phase has a kill criterion. **Do not advance a phase until the prior one beats its judge OOS.** The whole point of this project is to *connect* existing pieces, so most phases are wiring + one net-new piece, not greenfield modeling.

## Three binding constraints (read before anything)

1. **Sample is thin, not big.** ~7 events/day, day-clustered → the *day* is the independent unit (~25 independent OOS days on the current window). An 8-group feature stack on this is the exact overfit regime the repo already burned on ("4 mirages already" in ~2k events). Defense: ablate one family at a time; only the **day-block bootstrap delta-CI** (`hold_break_model.py`) decides whether a family stays.
2. **MBO is a 5-month single-regime layer.** Clean MBO cache = 112 trading days, all 2026 (`docs/DATA_MANIFEST.md`). Build the *entire baseline* on MBP-1 / TBBO (13 months, 342 days). MBO is an ablation experiment only; if it adds no OOS lift on 112 days it's decoration, and even a positive result carries severe regime-generalization risk.
3. **Lookahead is the default failure mode here.** Mira's deployed "edge" was a lookahead-selection artifact (features peeked into the trade's own first minute). Every feature must satisfy `t_feature_end ≤ t_decision`, enforced by `features.py::assert_no_lookahead` at build time, on every row.

## Phase 0 — scaffold (DONE 2026-06-14)

Spec, plan, reuse-map, stub skeleton. No model code. ← you are here.

## Phase 1 — reproduce the existing baseline, end to end

**Goal:** stand up the spine by *re-running* `market_state` Stage 1 through this project's `pipeline.py`, unchanged. **ES only** (exactly what `zone_events.py` runs today — `SYM = "ES.c.0"`), PDH/PDL only, OFI-only features, binary hold/break. Adding NQ is the first *extension* once the wiring is proven faithful, not part of the reproduce.

- `events.py` reuses `zone_events.precompute_levels` (1d-bar PDH/PDL — the actual Stage-1 source, NOT `levels.py`) + the touch-onset loop.
- `features.py` reuses `zone_events.cks_ofi_inc` etc. + adds `assert_no_lookahead`.
- `resolver.py::ofi_only_baseline` + `judge` reuse `hold_break_model.py`.

**Step 0 — capture reference (DONE 2026-06-14):** ran the two scripts on full 342-day data → [`report/phase1_reference.md`](report/phase1_reference.md). n=2856, `ofi_signed` OOS Spearman +0.281, OFI-only bootstrap AUC 0.630.

**Step 1a — reproduce through the spine (DONE 2026-06-14):** ✅ `verify_phase1.py smoke` = exact row match (79 rows); `verify_phase1.py full` = **EXACT MATCH on all 2856 rows × 9 cols**, and §2/§3 reprint identically. Decomposition is faithful. Kept the kernels (`cks_ofi_inc`, `label_touch`, `peer_ofi_stream`, `precompute_levels`) imported, not reimplemented.

**Step 1b — clean-reader swap (DONE 2026-06-14):** ✅ replaced raw `read_mbp1` (`[day, nxt)` UTC) with `read_mbp1_trading_day` (CME session window) and made it the **default reader**. `verify_phase1.py compare` showed the numbers moved by a clean, fully-attributable **session-boundary correction**: n 2856→2877 (+21), `ofi_signed` OOS +0.281→+0.299, OFI-only AUC 0.630→0.639, divergence still non-lifting. All 2,712 common (ts,level) rows byte-identical (0 label/dir/OFI changes); every moved row is in ET hours 17–20 (trading-day drops post-close/maintenance touches, folds the prev-evening session into the correct day). Adopted as canonical (user call). Raw kept as the `smoke` faithfulness guard. **Phase 1 CLOSED.**

- **Kill:** must reproduce Stage 1's OOS result bit-for-comparable. If the wiring changes the number, the wiring is wrong. No new modeling until this matches. *(Step 1a met this; Step 1b's move was an understood data-correctness fix, not a wiring bug.)*

## Phase 2 — expand events + multi-head resolver

**Goal:** the net-new modeling. Add overnight H/L, OR H/L, VWAP±bands as event families; add the multi-head outputs.

- `events.py`: wire full `levels.py` set; add families one at a time.
- `labels.py`: extend triple-barrier to `y_hold/y_break/y_chop`, `y_target_before_stop`, `realized_R`, `MAE_R`, `MFE_R`, `time_to_target`, `y_tail`.
- `resolver.py`: LightGBM multiclass (branch) + binary (target-before-stop) + quantile (MAE_R / expected_R); isotonic calibration per walk-forward fold.
- **Kill (per family):** a new event family or feature group stays **only if** it beats the OFI-only baseline OOS by a day-block bootstrap delta-CI that clears zero. Families that don't lift are dropped, not "kept for completeness."
- **Kill (calibration):** predicted-60% bucket must win ≈ 60% OOS, or the probabilities are not tradeable.

## Phase 3 — conditioner (Type A first)

**Goal:** turn resolver outputs into `size_mult ∈ {0,.25,.5,.75,1}`.

- `conditioner.py` adopts `risk_conditioner_v0/feature_schema.yaml` + the Type A head architecture (start with the less-controversial Type A path; defer Type B until its labels are re-verified).
- **Kill:** conditioner must reduce p95 MAE_R / tail without eroding net_R by more than a few % OOS (reuse `risk_conditioner_v0` kill thresholds). If it only over-filters (kills net_R for marginal tail reduction), it fails.

## Phase 4 — prop governor + honest economics

**Goal:** account-safe sizing under real firm rules, with honest fills.

- `governor.py` reuses `sizing_v1/account.py` + `sizing.py::vol_targeted` + `risk_manager.py` + `prop_model_v0/eval_ev.py`; **adds intraday bar-grain MTM** for within-day DLL breach detection (the real gap).
- Fills: tick-replay path (reuse `reclaim_entry.py::seq_r` or extend the broker with a ticks param) so entries/exits are `fill_confidence='exact'`, not conservative. Honor `CLAUDE.md §8`.
- **Kill:** the governed system must improve **pass / reward probability** and cut p95 daily-loss vs the ungoverned version in `eval_ev` Monte Carlo across multiple firms — not just raise Sharpe.

## Phase 5 — earn complexity (only if Phases 1–4 pass)

In order, each gated by the same OOS judge: MBO depth layer (on the 112-day window, eyes open) → options/GEX **interaction** terms (prove the interaction; standalone is already dead) → sequence/TSFM embeddings as features → mixture-of-experts. **None of these are assumed-good.** The repo's prior is that most of them are decoration until proven otherwise.

## Definition of done (v0)

Every line in the SPEC scorecard holds OOS, the OFI-only judge is beaten by a day-block bootstrap CI clearing zero, calibration holds, and `eval_ev` shows improved pass-rate + lower p95 daily loss on ≥2 firms. Anything short of that is a NULL result — and a documented NULL is a valid, shippable outcome for this lab.
