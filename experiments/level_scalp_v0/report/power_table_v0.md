# Power table v0 — 2026-06-11 (counts only; NO reaction stats unblinded)

Run: SELECTION window 2025-05-01 → 2025-12-31, 150 non-roll trading days, tier-1 +
round-number families, ES/NQ/YM/RTY. Artifacts: `out/touches_p0_{SYM}.parquet`,
`out/power_table.parquet` + manifest. 33,643 touches total (ES 8,215 / NQ 8,134 /
YM 8,963 / RTY 8,331). **70/80 family×symbol cells pass the C21 gate (n≥200, days≥60).**

## Facts that affect the design (all pre-unblinding — legal to act on)

1. **Prior-week H/L is unpowered everywhere.** pwh/pwl fail the gate on all 4 symbols
   (n = 68–206, days 15–49): price simply doesn't reach the prior week's extremes often
   enough. pwc is marginal (ES/RTY pass, NQ/YM fail by 1–3 days).
   → **Primary cell #3 (prior-week H/L × ES × RTH) cannot carry gating authority** and
   must be swapped before the freeze. Recommendation: replace with `pdc × ES × on+pre`
   (n=833, the overnight magnet construction) or `onh/onl × NQ × open` — Ben's call.
2. **Spread widens at the touch.** ES unconditional RTH median = 1.0 tick (verified
   2025-05-02, n=5.0M RTH rows) but median spread AT touch onsets = 2.0 ticks across
   nearly all families/symbols. Liquidity pulls exactly when price sweeps into a level.
   Atlas cost walls must use touch-conditional spreads (they're recorded per touch).
3. **Spread regime drift 2025→2026.** NQ touch-median here (2025) is ~2 ticks; the
   2026 measurements used for the PLAN cost table showed 3 (p90 4–5). SELECTION-window
   economics are cheaper than CONFIRMATION/HOLDOUT economics — the confirmation pass
   re-prices with its own window's spreads; do not carry 2025 walls forward.
4. **Round numbers are the volume family** (1,573–2,659 touches/symbol) — the gate's
   power workhorse, as expected for the whitespace primary cells (#5/#6).
5. **Validity enforcement is visible in the data**: 09:30-valid families (onh/onl, pm,
   london, or, rth_open, gap_pdc) show exactly zero on/pre-bucket touches.
6. first_touch_share runs 0.16–0.43 → Nth-touch effects will have sample to measure.

## Addendum (2026-06-11 late) — defend-size re-run + wall-cell power check

Power table re-generated with the at-touch defending-size feature (MECHANISMS.md #2b).
Counts-only observations:
- **Depth stacks at levels**: median defend_sz_norm at touches is 1.3–2.2× the day
  median (ES 1.83, NQ 1.50, YM 1.33, RTY 2.20) — the Kavajecz–Odders-White depth-peak
  mechanism is visible in our data before any outcome is unblinded.
- **Proposed wall-conditioned primary cell is powered**: (pdh+pdl+onh+onl) × RTH ×
  defend_sz_norm ≥ 2 → ES n=530/137d, NQ 370/126, YM 239/116, RTY 584/136 (all clear
  the 200/60 gate). Caveat: a fixed 2× threshold is less selective on RTY (median 2.2)
  than on YM (median 1.33) — the pre-registered cell is ES-only.
- round × RTY × RTH: n=952/138d (candidate replacement for the VP POC primary).

## Still missing before the atlas can unblind

- Tier-2 builders: session VWAP ±σ bands (primary #7), prior-day VP POC/VAH/VAL (primary
  #8), FVG zones, equal H/L — power-table counts must be appended for those families.
- Tier-3: gamma walls (blocked on the theta backfill regen), MBO depth clusters.
- Atlas outcome stage: three-way reaction grid on exit-side quotes + selection-aware
  bootstrap (`boot()` with in-resample re-selection + joint-symbol day draw).
- External research reconciliation (`report/external_research.md`) — pending GPT run.
