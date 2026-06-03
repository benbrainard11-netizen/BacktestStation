# market_state — intraday "zone-touch → hold/break" system (design, v1)

Status: design locked 2026-06-03, pre-build. The honest evolution of "institution zones": you can't predict
direction, but at a level you can model the **resolution** (hold vs break) and play both branches. This is
**Mira, generalized** — and it lives or dies by one benchmark: **does it beat an order-flow-only model OOS?**

## What it predicts (not direction)
Fires only on a **zone-touch event**; outputs P(hold) / P(break) + expected R. You wait for confirmation; it
hands you the branch odds and the tell. Mira's reclaim recipe stretched to more level types.

## Architecture (event-driven, level-anchored — NOT bar-driven)
`detect zones → detect touch events → triple-barrier hold/break label → event-time microstructure features
@ the touch → LightGBM → walk-forward OOS + ablation → live scenario odds`

## The label (reuse triple-barrier)
Touch at τ when signed dist d_t ∈ [−ε,0] (ε≈1–2 ticks). **break** if price reaches +b within horizon and holds;
**hold** if it first moves to −r. In TICKS, not bps. Reuse `orderflow_lgbm_probe_v0/triple_barrier_experiment.py:
relabel_triple_barrier()` (exits at the barrier = honest stop economics). Drop same-bar-ambiguous (stop rule).

## Features — tiers (from the 2026-06-03 deep-research review; out/deepresearch_level_features.txt)
Deep research = CANDIDATE features only. Each earns its seat by ABLATION on ES, not by literature.
KEY FINDING: the edge is **event-time (100ms–2s windows AT the touch)**, NOT the 15-min buckets the old
bookproxy code used. So we build NEW event-time features; the 15-min stack is a coarse REGIME/context layer only.

- **Tier 1 — build first (MBP-1 top-of-book, ~1yr on disk):**
  - **CKS OFI** (Cont-Kukanov-Stoikov best-bid/ask) — EXACT on MBP-1, the single most robust feature. Banded around L.
  - **Signed aggressor volume** (use tbbo aggressor side; at-level vs through-level split).
  - **Top-of-book depth / queue imbalance** (qB−qA)/(qB+qA), persistence/age-weighted to resist spoofing.
- **Tier 2 — upgrade (MBO full depth, only ~5mo on disk → LOW POWER, ablate honestly):**
  - banded depth asymmetry + slope, queue depletion/refill (position via OrderID/PriorityID), absorption/native-
    iceberg (same-OrderID refill), sweep-resiliency. Research rates these high but they need real MBO → we have
    only Jan–May 2026. Build as a premium layer on the overlap; keep only if they beat Tier-1 OOS.
- **Tier 3 — conditioner (ES qualifies, deep same-day options):** dealer gamma / 0DTE as **interaction only**
  (`OFI × I(GEX<0)`, `|GEX|`), NEVER standalone — exactly the resolution we reached. OI-only GEX = weak prior;
  re-earn its seat via ablation. (We already have SPX EOD GEX from options_signals_v0.)
- **SKIP — VPIN** (research verdict: mostly hype here; not event-local).
- **Context layer (cheap, reuse):** vol regime (validated tile), realized vol, time-of-day, the old 15-min bookproxy
  as a regime proxy. These condition WHICH zones get respected (the "regime respects some zones more" idea).

## Zones (attention anchors — NOT the edge)
Objective, pre-registered, small set: VPOC + volume nodes (HVN/LVN), prior-day & overnight H/L, session VWAP±σ,
opening range, round numbers. Each zone type is a FEATURE; none assumed magic. Research is explicit: level
families are "attention anchors," the microstructure decides hold/break. (No FVG/order-block chart patterns —
those died as wick-noise/lookahead artifacts.)

## The judge (reuse, non-negotiable)
- Walk-forward, **purged + embargoed** splits (`run_walk_forward_chooser.py:split_for_fold()`).
- **Baseline = event-time OFI-only model.** The full system must beat it OOS. If zones/MBO-depth/gamma don't lift
  it, they're decoration → drop.
- **Ablation** by feature group = how each (zones, MBO-depth, gamma, regime) earns or loses its seat.
- Honest costs (`training.py` cost model) + honest_economics R.

## Data reality (checked 2026-06-03, D:\data\raw\databento)
- ES.c.0 **mbp-1**: 333 days, 2025-05-01 → 2026-05-27 (~1yr, top-of-book). The baseline's home.
- ES.c.0 **mbo**: 124 days, 2026-01-01 → 2026-05-27 (~5mo, full depth). Tier-2 upgrade only.
- ES.c.0 **tbbo**: 315 days (trades+BBO, aggressor side for signed volume).
- Events detectable on 5m bars back to 2023, but FEATURES (the edge) only exist 2025-05+ → modeled sample ≈ 1yr.

## Honest constraints (hold these)
1. ~1yr of order-book data = thousands of touch events but only **one year of market conditions** → regime-
   generalization risk (Mira's "Jan is one month" lesson, scaled). OOS is within-year walk-forward, not multi-regime.
2. Level families are unproven anchors; the microstructure is the testable edge.
3. Full-depth MBO features (the literature's favorites) have only ~5mo → easy to overfit; ablate ruthlessly.
4. The whole thing must beat the OFI baseline OOS or the complexity isn't earned.

## Reuse map (orderflow_lgbm_probe_v0 — don't re-plumb)
event template `mtf_sweep_reclaim.py:sim()` · label `relabel_triple_barrier()` · 15-min feats `feature_sets.py:
add_orderflow_structure()` (context layer only) · train/eval `training.py:train_one_from_parts()` · splits
`run_walk_forward_chooser.py` · data `read_mbp1()/read_mbo()`. NEW code = zone detector + event-time feature layer.

## Build stages
1. **Events + labels + OFI baseline (the go/no-go)** — DONE 2026-06-03, **PASS**. `intraday/zone_events.py`:
   PDH/PDL touches, event-time CKS OFI [t0,t0+2s], triple-barrier hold/break (outcome measured AFTER the OFI
   window = no lookahead). 90 sampled days, n=763, break rate 40%. OFI->break: IS Spearman +0.16, **OOS +0.26
   (n=174)**, break rate 32/38/51% by OFI tercile. OOS regressed from a thin-sample +0.43 toward IS = believable,
   not luck. CAVEATS: events day-clustered (~7/day -> OOS ~25 indep days; p optimistic, add day-blocked CIs);
   modest effect; OFI-only on PDH/PDL; ~1yr of conditions. Brick holds -> proceed.
2. Full Tier-1 (signed vol + depth/queue imbalance) on ~1yr MBP-1.
3. Tier-2 MBO-depth upgrade on the ~5mo overlap; ablate vs Tier-1.
4. Gamma conditioner (interaction); ablate.
5. Live scenario output: today's zones + P(hold)/P(break) + the tell.
