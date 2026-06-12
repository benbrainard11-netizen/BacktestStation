# level_scalp_v0 — level-reaction scalp study

**Question:** are there pre-known price levels (or detectable events at them) where the
short-horizon reaction is reliably positive after honest fills and stressed per-symbol
costs — tradeable as scalps (small tick targets, minutes-scale holds), entered either by
a resting limit at the level (maker) or an event-trigger after the touch (taker)?

**Status:** Phase 0 (touch atlas) — scaffolded 2026-06-11, no code yet. PLAN v0.2 after a
3-lens adversarial review ([report/plan_review_2026-06-11.md](report/plan_review_2026-06-11.md))
caught 8 blockers in v0.1 (level validity, oracle placement, MBO book warm-up, toothless
kill gates, holdout budget, NQ spread reality, exit-side fills, queue circularity).
**Spec:** [PLAN.md](PLAN.md) — FREEZES at first atlas run (touch constants, primary cells,
fill rules); later changes spawn a successor judged on new calendar data only.
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
