# LTF cross-asset SMT definition — does a better definition add EDGE or just COVERAGE?

**Date:** 2026-06-08 · **Bench/additive only — no live artifact touched.** Scripts in
`experiments/smt_ltf_bench/`. Window: 2025-09-01 → 2026-05-22, ES/NQ/YM/RTY, 7 TFs.

## TL;DR — it's COVERAGE, not EDGE. Keep the adjacent-candle definition.
A higher-coverage SMT definition catches ~50–84% more divergences, but those extra divergences are
**equal-or-worse** quality. The "obvious fix" (window/N-bar lookback) is **significantly WORSE** at the
core LTFs. No variant clearly beats the adjacent baseline on tradeable edge. This is fully consistent
with the deployed gate, where SMT features are near-zero importance and the edge is MBO orderflow — so
a better SMT *flavor* cannot move the needle. **Do not change the live SMT definition for edge.**

## Phase 0 — ground truth (confirmed by reading the code)
- Live LTF SMT = `SmtPrevCandleDivergenceDetector` (`backend/app/research/detectors/smt_prev_candle_divergence.py`,
  with the 5m mode in the vendored/live copy). Logic: at each TF, **immediately-previous candle** ref;
  high-side swept = `cur_high > prev_high`; fires when `0 < #swept < 4` across the basket. No window.
- Label = `extreme_hold_move` (`mira_trigger_v0/build_trigger_candidates._target_features` @60m +
  `probe_pdh_pdl`): **(extreme NOT rebroken by >1 tick) AND (price moved ≥8 ticks away)** over [t, t+60m].
  Reproduced exactly; measured on the PRIMARY swept symbol vs its sweep extreme.
- `read_bars` resample verified byte-identical to my in-bench resample (15m ES, n=3257).

## Phase 1 — label-edge per definition (8.5 months, robust N)
success = forward `extreme_hold_move`@60m; `z` = two-proportion z vs adjacent at the same TF.

| TF | adjacent | window3 | window6 | swing3 | fvg |
|---|--|--|--|--|--|
| 5m  | **0.204** (n36110) | 0.206 (z+0.5) | 0.205 (0.0) | 0.208 (+1.0) | **0.217 (z+4.2)** |
| 15m | **0.327** (n11578) | 0.309 (z−2.9) | 0.302 (**z−3.8**) | 0.321 (−1.0) | 0.329 (+0.3) |
| 30m | **0.413** (n5689)  | 0.392 (z−2.3) | 0.384 (**z−3.0**) | 0.419 (+0.6) | 0.423 (+1.1) |
| 1h  | **0.504** (n2792)  | 0.483 (−1.5)  | 0.485 (−1.3)  | 0.525 (+1.6) | 0.526 (+1.7) |
| 90m | **0.564** (n1902)  | 0.536 (−1.7)  | 0.541 (−1.3)  | 0.567 (+0.2) | 0.580 (+1.1) |
| 4h  | **0.704** (n699)   | 0.706         | 0.713 (+0.4)  | 0.715 (+0.5) | 0.719 (+0.7) |
| 6h  | **0.728** (n459)   | 0.755 (+0.9)  | 0.742         | 0.737        | 0.755 (+1.0) |

(LTF base success rises with TF: 5m ~0.20 → 6h ~0.73. The often-quoted ~46% is the post-*level-sweep*
setup population; raw SMT-event base is TF-dependent. Comparison that matters = variant vs adjacent.)

### Ranking by edge
1. **FVG-anchored** — only variant never worse; significantly better at 5m (z+4.2, but +0.012 absolute)
   and marginally at 1h/30m. Adds the most coverage. Gains are small.
2. **Swing-anchored** — ≈ adjacent everywhere (no significant lift); pure coverage.
3. **Adjacent (baseline)** — strong; best per-setup at the tradeable mid-TFs.
4. **Window / N-bar (the motivated "gap fix")** — **WORSE**: significantly below adjacent at 15m/30m
   (z −2.3 to −3.8). **Flag: does not beat baseline — it hurts.**

## Miss-rate analysis (RQ1) — the gap is real, but the missed setups are worse
Window catches divergences adjacent misses, but the missed population is **significantly lower quality**:

| TF | window6 extra coverage | new-event success | adjacent success | z(new vs adj) |
|---|--|--|--|--|
| 5m  | +52% | 0.195 | 0.204 | −2.4 |
| 15m | +52% | **0.287** | **0.327** | **−4.9** |
| 30m | +52% | 0.361 | 0.413 | **−4.2** |
| 90m | +51% | 0.521 | 0.564 | −2.0 |

Swing's extra ~84% and FVG's extra ~80% are ≈ adjacent quality (FVG slightly better at 5m). So the
non-adjacent divergences window catches are **mostly weaker reversals** — adjacency is itself a freshness/
momentum quality filter, not an arbitrary limitation.

### Worked examples — 15m divergences adjacent MISSED (caught by window6)
```
2026-05-21 14:30 UTC  low  NQ  ext=29127  (success=1)   <- non-adjacent low-sweep, held+moved
2026-05-21 15:45 UTC  low  YM  ext=49919  (success=1)
2026-05-21 19:00 UTC  low  ES  ext= 7438  (success=1)
```
These illustrate the gap (like the live 10:05→10:17 case) — real divergences the adjacent detector never
tags. But on average across 8.5 months the missed 15m set scores **0.287 vs 0.327** — catching them
**dilutes** edge.

## Recommendation (RQ3/RQ4)
- **Do NOT replace adjacent with a window/N-bar detector** — it measurably lowers per-setup edge at the
  core LTFs (15m/30m).
- **No definition is worth changing the live SMT for EDGE.** The deployed gate's edge is orderflow; SMT
  flavor is low-importance, so this is expected. Phase-1 confirms it empirically.
- **If the goal is more setups (coverage), FVG-anchored is the marginal best** (+coverage at ≈equal/
  slightly-better quality, best at 5m/1h) and **swing-anchored** is the next (equal quality). Either could
  be added as an *additional* `post_sweep_smt` source feeding the orderflow gate — but expect
  **same per-setup edge**, just more frequency. They are cheap (bar-only, same recompute cadence).
- **This will NOT fix the live under-trading** — that was operational (reconnect/lockout) + a zero-
  post_sweep_smt regime, not a missing-SMT-definition problem (see UNDERTRADING_DIAGNOSIS.md).

## Phase 2 — NOT run (by design)
Methodology gate: escalate to wire-in + retrain only if a variant *clearly* beats adjacent. None does
(best is FVG +0.012 at 5m / marginal +0.02 at 1h, not a tradeable edge gain). The cheap Phase-1 work
answered the question; a retrain would burn compute to chase noise.

**If you still want the coverage play tested:** the cheapest Phase-2 is to add FVG-anchored SMT as an
extra source in `build_trigger_candidates`, regenerate, and score with the EXISTING gate (no retrain) to
see if the new setups (a) pass the gate at a similar rate and (b) carry similar orderflow R. That tests
COVERAGE→tradeable-frequency without claiming edge. Flagged, not done.

## Follow-up: 1m/3m swing SMT + the CONDITIONAL (post-PDL-sweep) test
Prompted by the idea "use 1m/3m swing SMT after a PDL sweep in the AM, enter the reversal."
- **Standalone 1m/3m swing SMT** (`smt_bench.py --tfs 1m,3m,5m`): swing3 IS significantly > adjacent at
  1m (0.114 vs 0.108, z+3.9) — but on an ~11% base with a +0.6pp effect that's significant only from
  N≈85k. Economically negligible standalone.
- **Conditional test** (`conditional_pdl_smt.py`): AM PDL/PDH sweep → reclaim → fixed_2R, stop = swept
  extreme (== Mira's smt_pivot_180s, so this isolates SIGNAL not stop). The stop is the same either way.
  - 4.5mo (n=215): +1m-SMT +0.310 vs no +0.098 (Δ+0.21, t=1.14, NOT sig).
  - **2yr (n=1041): +1m-SMT +0.354 vs no +0.284 (Δ+0.07, t=0.81, NOT sig — washed out).**
  - adjacent 5m/15m SMT also adds nothing conditional (+0.317 vs +0.345).
  - **But the AM PDL/PDH sweep+reclaim itself is a clean +0.333R / 49.9% win edge (n=1041, 2yr), model-
    free, simple extreme stop.** THAT is the tradeable structure — the SMT flavor (fine or coarse) is
    decoration on it. Likely the 1m SMT is just a visible PROXY for the orderflow at the reclaim (the
    real edge), so it correlates without adding independent signal.
  - Verdict: the 1m-swing-SMT idea does not add edge once powered properly; consistent with the rest.

## Reproduce
- `experiments/smt_ltf_bench/smt_bench.py` — all variants, label, table, miss analysis (8.5mo, 7 TFs, ~18s).
- `experiments/smt_ltf_bench/smt_window_divergence.py` — additive registered detector (new window modes),
  for the optional coverage path; does not touch the live detector.
- Outputs: `out/phase1_variant_tf_edge.csv`, `out/phase1_miss_analysis.csv`.
