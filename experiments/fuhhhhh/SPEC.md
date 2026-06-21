# SPEC — the constitution

This file is binding. Tests that violate it don't count, in either direction.
Adapted from the GPT-5.5 research spec + this repo's paid-for lessons
(sources: mira_parity_audit, prop_model_v0, level_scalp_v0, mira_gate_harness,
upgraded_mira — see PRIOR_ART.md).

## 1. Goal

A growable, staged model that predicts **objective-first outcomes** on ES intraday:

- P(upside objective touched before downside invalidation, within N minutes)
- P(downside objective first)
- P(neither / no clean setup)

Options positioning supplies *context and candidate objectives*; futures microstructure
supplies *confirmation and timing*. The trading engine (deterministic rules + hard risk
limits) decides; the model only emits calibrated probabilities.

Success is measured in **realized R after honest fills and costs**, and ultimately in
**payout-adjusted prop-account survival EV** — not Sharpe, not accuracy, not label hit-rate.

## 2. Universe and windows

- Options root: **SPXW** (SPX weeklies, ThetaData). SPY not available locally; NDX/NQ is
  an extension (vendor greeks cap — see DATA.md).
- Futures: **ES.c.0**. MES does not exist locally; size in MES units ($5/pt) off ES prices.
- Session: RTH only, decisions on a 5-minute grid **09:35–15:45 ET**, flat by firm cutoff
  (earliest relevant: 16:10 ET MFFU/Topstep). No overnight holds.
- **Dev window: 2025-05-01 → 2026-03-31** (intraday options data + ES MBP-1 both exist).
- **Sealed holdout: 2026-04-01 → data end (2026-06-05 intraday / 2026-06-09 bars).**
  Lifetime read budget: **2 reads**, logged in HOLDOUT_LEDGER.md. Primaries must be
  registered in this file *before* read #1. Walk-forward OOS inside the dev window is
  the everyday honesty mechanism; the holdout is the final word.
- Deep history (2017→2026, EOD greeks/walls + 1m bars) is for **event studies and regime
  context only** — daily-grain modeling on it is closed territory (PRIOR_ART §1.7).

## 3. Architecture (three stages + a hard risk shell)

1. **Regime/context stage** — starts as *features*, not a separate model: gamma-sign
   proxy (multiple sign conventions, see rule 4), 0DTE share, wall density, IV context,
   day type. NOTE: gamma-SIGN as a standalone day filter is dead on replication
   (PRIOR_ART §1.5) — regimes enter only as interaction features / split diagnostics.
2. **Objective + label stage** — the heart. At each grid time t: nearest meaningful
   objective above and below from the level families (gamma wall zones, zero-gamma, pin,
   PDH/PDL, ONH/ONL, opening range, VWAP bands, prior settle). Triple-barrier race label:
   objective barrier / invalidation barrier / time barrier (45 min primary; 30/60 swept
   as registered secondaries).
3. **Entry-confirmation stage** — futures microstructure at t: CKS OFI, CVD, book
   imbalance, sweep/absorption flags, distance features, realized-vol state, time-of-day.
4. **Risk shell (rules, never model output):** fixed per-trade risk, fixed daily max
   loss, max trades/day, cooldown after loss, no entries after cutoff, news blackout
   optional. Encoded against `prop_model_v0/funnel_specs.py` firm mechanics.

## 4. Hard rules (each one is a lesson someone already paid for)

1. **Feature-window ≤ decision time, asserted at build time.** Every feature builder
   asserts max(feature timestamp) ≤ decision timestamp. Two champions died from this
   (Mira bookproxy [−30s,+60s) gate; prop_model UTC-panel peer-close leak). Use
   `common.assert_no_lookahead`.
2. **T-1 options discipline.** EOD greeks/OI/walls from day D−1 are the only EOD inputs
   to day D. Intraday flow features use only prints ≤ t. OI is not a live feed.
   Inherited artifacts must be *audited* for this before reuse (phase 0) — do not assume.
3. **Walls are zones, not prices.** ±k ticks, k registered before testing (default ±8
   ES ticks = ±2 pts; sweep registered, not fished).
4. **GEX is a proxy, not an x-ray.** Test sign conventions as a battery (calls+/puts−,
   inverted, absolute-only, 0DTE-only, all-expiry, near-spot-only). If exactly one weird
   convention works in one sample, it's overfit, not discovery.
5. **Geometry first.** Any race/first-touch claim must beat the **distance-only
   geometric baseline** (daily wall-race IC was +0.786 from pure geometry). Any
   level-specific claim must beat a **shuffled-distance placebo** (non-tautological —
   the v1 wall-rotation placebo was same-price-by-construction and had to be redone).
   Autopsy positive trades for pre-decided entries (24/29 wall-race "wins" had price
   already gapped through the wall at open).
6. **Honest fills or it didn't happen.** Stop-vs-target ties: stop wins (CLAUDE.md §8).
   Stops clear level/swing extremes by ≥2–4 ticks (stop-at-extreme = −0.6R, 90% stopped).
   Bar-level R must converge under tick-by-tick MBP-1 re-fill
   (`mira_upgraded_v0/fill_realism.py`) before any number is believed. Costs per-symbol:
   $3.80 round-trip + 1 tick/side slippage on ES, stressed up in phase 5.
7. **No random splits.** Purged walk-forward (expanding train, embargo ≥ label horizon),
   copied from `btc_model_v0/model_wf.py`, with its **mandatory shuffled-target negative
   control** (abort if |control IC| > 0.05). Overlapping 45-min labels on a 5-min grid
   are heavily autocorrelated — purge accordingly, and use day-block bootstrap for CIs.
8. **Realized R is the objective.** Label accuracy / AUC are diagnostics only (Mira
   retrain: AUC 0.81 with realized R −0.137).
9. **Replication before belief.** Per-window noise ≈ ±0.15R. Any filter/feature claim
   needs multi-month consistency (and multi-symbol once extended). Single-window lifts
   are presumed noise.
10. **Era ablation.** A feature block's claimed lift must survive removing the block on
    the same era (gex-era IC +0.133 *with* gx vs +0.166 *without* = the regime, not the
    options). Mean per-fold IC, not pooled.
11. **No graveyard re-litigation.** Constructions in PRIOR_ART.md marked KILLED are not
    re-run unless a materially new mechanism is registered in LEDGER.md *first*, naming
    what's different and why the prior kill doesn't apply.
12. **Diagnose, don't declare — but verdicts lock.** Every negative result names the
    failing component (options features / futures features / labels / objective def /
    execution / model) with the evidence that distinguishes it from "no edge." A single
    failed test never closes the program. Conversely: each registered construction gets
    **one revision cycle**; after that its verdict locks. No infinite re-litigation in
    either direction.
13. **Pipeline guards.** Never cache 0 rows; assert in-window event counts > 0; every
    dataset/artifact carries a manifest (git SHA, params, source row hash). A silent
    0-row build once produced a fake 6-month robustness result here.
14. **Prop-realistic behavior.** Low-to-moderate trade count, defined stop, no sim-fill
    exploitation, no sub-10s scalps (Tradeify 10s/50% gate; Rithmic sim queue rules).
    Honest-fill backtesting doubles as compliance armor.

## 5. Phases — MODEL-FIRST (restructured 2026-06-12 at Ben's direction)

The combined options+futures model is the centerpiece and gets built FIRST, in full.
Controls (geometry floor, ablations, shuffled-target, no-lookahead asserts) live
*inside* the system as embedded diagnostics — they are NOT gates that delay the build.
Event studies are debugging tools used when something looks off, never prerequisites.
A weak iteration produces a diagnosis and the next growth step, not a verdict.

**Phase 0 — data sanity + inherited-artifact audit.** DONE 2026-06-12 (LEDGER P0.1–P0.5).

**Phase 1 — build the full system (v0), end to end.**
All of it, together: options feature engine (intraday GEX/flow/IV ≤ t + T-1 EOD
context), futures feature engine (returns/vol/VWAP/session levels/time), objective
engine (nearest level above/below from all families), triple-barrier race labels
(conservative ties), dataset builder with build-time no-lookahead asserts, LightGBM
3-class walk-forward (purged, day-block, embargoed) with calibrated probabilities and
realized-R evaluation. Embedded ablations of the SAME system: geometry-only floor /
futures+geometry / options+geometry / combined. Shuffled-target control wired in.
*Output:* dataset + model + report_v0. Whatever the numbers say, v0 is iteration zero
of a system we grow — not a pass/fail event.

**Phase 2 — grow it (the loop Ben actually wants).**
Ranked growth increments, each judged by dev-OOS realized-R delta vs the previous
iteration (rule 9 replication applies): MBP-1 order-flow features (OFI/CVD/sweeps —
the entry-confirmation stage), regime interactions, EV-threshold trading layer on
calibrated probs, objective-family expansion, NQ/RTY/YM replication, sequence models
last. Each increment gets a LEDGER entry; weak increments get dropped, the system
keeps growing.

**Phase 3 — honest fills + cost stress.** Tick-level re-fill convergence
(`fill_realism.py` pattern), stop-buffer sweep, slippage/commission stress ladder.
Required before any number is quoted as money (rule 6) — but it verifies the built
system, it doesn't precede it.

**Phase 4 — prop simulation.** Trade list → `sizing_v1` account state machine +
`prop_model_v0/funnel_specs.py` mechanics + `eval_ev.py` campaign EV. Metric:
payout-adjusted survival across Apex/MFFU/Topstep/Lucid/Tradeify configs. Day-block
bootstrap MC (preserves loss clustering).

**Phase 5 — shadow logging.** Only after 1–4. Live plumbing deferred until then.

**Program-level park condition (narrow, unchanged in spirit):** only if the grown
system — after the order-flow increment at minimum — still can't beat the
geometry-only floor on dev OOS across multiple months does the program park. No single
iteration, ablation, or test can park it (rule 12).

## 6. Growth / extension points (in priority order, each through the same gauntlet)

- NQ chain: compute NDX greeks from raw quotes+OI (IV→BS gamma) to beat the vendor cap.
- Deep intraday-GEX reconstruction 2017→2026: T-1 EOD chain repriced at ES-derived spot.
- Intraday options *trade-flow* upgrades (the open door named in the standing verdict).
- New objective families; RTY/YM replication; regime classifier as its own stage.
- Sequence models (TCN / small transformer): **only** after the tabular pipeline is
  stable and positive — not before, per the origin spec and common sense.
