# level_scalp_v0 — level-reaction scalp study

**Question:** are there pre-known price levels (or detectable events at them) where the
short-horizon reaction is reliably positive after honest fills and stressed per-symbol
costs — tradeable as scalps (small tick targets, minutes-scale holds), entered either by
a resting limit at the level (maker) or an event-trigger after the touch (taker)?

**Status: PARKED 2026-06-12 — three constructions tested honestly, all null; reusable
harness + one strong successor lead.** Arc: (1) classic-level scalp = NULL (adverse
selection, [phase1_mode_a.md](report/phase1_mode_a.md)); (2) sim-venue resurrection =
killed on engine + compliance ([sim_venue_verdict.md](report/sim_venue_verdict.md));
(3) defender/iceberg family = reaction REAL (+3t pre-registered screen,
[defender_atlas.md](report/defender_atlas.md)) but uncapturable — resolves in ~7s at a
price no implementable entry transacts at ([defender_fills.md](report/defender_fills.md),
[defender_late_taker.md](report/defender_late_taker.md)). **Successor lead (surfaced
twice independently): the INVERSION — defense-break continuation (through-fills ran 97%
continuation). Untested.** Holdout 2026-04→06-09 never read; both lifetime shots intact.

**Original framing (2026-06-12 morning):** Phase 0 atlas found a real
gross reaction at ES/RTY levels (4/8 pre-registered cells cleared the maker wall,
[atlas_v0.md](report/atlas_v0.md)); Phase 1 honest-fill confirmation
([phase1_mode_a.md](report/phase1_mode_a.md)) killed it: adverse selection is near-total
(the touches that don't fill you are the perfect rejections; E[react|no-fill]=+8.0 vs
E[react|filled]≈0) and stop gap-through adds ~2 ticks/stop → net −2.7 ticks/fill pooled.
**The holdout (2026-04→06) was NEVER read — both lifetime shots intact.** Successor
avenues (placement-at-creation queue seat, wider stops, fill-as-continuation-signal,
Mode B deep-target asia) are documented in the Phase 1 diagnosis; any successor is a new
spec per the PLAN post-null clause.
**Spec:** [PLAN.md](PLAN.md) — frozen at the 2026-06-11 atlas run.
**Keeper artifacts regardless of verdict:** the retest/overshoot table (atlas_v0), the
constitution + harness (valid_from levels, behind-you fill rule, selection-aware boot),
[MECHANISMS.md](MECHANISMS.md), and the external research reconciliation.
**External research:** [deep_research_prompt.md](deep_research_prompt.md) — copyable
prompt for GPT-5.5-Pro / Claude deep research on level types + queue-fill modeling.

## Why this is not Mira again

- Different **geometry**: 2–12 tick targets, sub-30-minute holds — vs Mira's 1–3R
  structural targets at 15–120m horizons. Never tested in this repo.
- Different **families**: round numbers, VWAP bands, volume-profile nodes, resting-MBO
  liquidity, multi-year gamma walls — all documented whitespace (no prior work).
- Different **entry economics**: passive/maker fill modeling (queue position, earn the
  spread) was twice identified as "the form that would work" and never built.
- **Legality-first**: every hard rule from the 2026-06-11 Mira look-ahead audit is a
  build-time constraint here, not a review item. See PLAN §Non-negotiables.

## Data this study runs on (verified on disk 2026-06-11)

| layer | coverage | role |
|---|---|---|
| MBP-1 ES/NQ/YM/RTY | 2025-05-01 → 2026-06-09, continuous | touch detection + honest fill replay (THE spine) |
| MBO ES/NQ/YM/RTY | 2026-01-01 → 2026-06-09 (~112 trading days, clean trading-day cut) | queue model, resting-liquidity levels (2026-only overlay) |
| 1m bars ES/NQ/YM (2015+), RTY (2018+) | → 2026-06-09 | level *construction* only — never touch pricing (wick artifacts) |
| Options EOD (SPX/NDX/RUT/DJX) | 2015→2026 backfill running 2026-06-11 | gamma-wall levels (prior-day chains only) |

## Run

All scripts: `backend/.venv/Scripts/python.exe experiments/level_scalp_v0/<script>.py`
from repo root. Artifacts → `out/` (disposable), reports → `report/`.
