# prop_futures_v0 — which CME instrument + day-flat intraday edge is the best prop-firm vehicle?

**Question.** The index complex (ES/NQ/YM/RTY) is heavily arbed and its one apparent
intraday edge (Mira reclaim) was exposed as look-ahead. The lab's one *robust* edge
(energy RV cointegration, OOS Sharpe +1.44) is **multi-day → not prop-compatible**
(prop firms force flat-by-close, Topstep excepted). So the open territory is the **27
non-index CME instruments** (energy / metals / rates / grains / FX / crypto), which have
never been systematically mined for a **day-flat intraday** edge.

This module asks: *across all 31 instruments we have data for, which has (a) the
liquidity to trade at prop scale, (b) enough intraday range to clear a prop target
before the daily-loss limit, and (c) an exploitable day-flat structure — possibly
enhanced by the cross-asset / options / equity data we already own?*

This is **prop_model_v0's Layer 2 (the trade generator) realized**, but instrument-
agnostic. Layer-1 economics (`prop_model_v0/report/eval_ev_v0.md`) and the money layer
(`sizing_v1`) already exist; this picks the *vehicle* and *edge* that feed them.

## Hard constraints (the prop reality — set before any result)

1. **Day-flat.** Flat by session close. No overnight, no multi-day holds. (Topstep is
   the only audited firm that allows overnight — treated as a secondary lane, not the
   primary design target.) This is why the energy RV book does **not** qualify.
2. **Prop scale = micros, thin budgets.** A ~50k eval carries ~$2.0–2.5k trailing DD,
   ~$1.1k daily loss, ~$3k target. A trade's stop has to fit inside that in dollar
   terms. So an instrument's **$-per-tick × typical stop distance** must leave room for
   a multi-R day. Ranked in ticks (scale-free) first, then in dollars.
3. **Honest costs from real book.** Spread + slippage charged from the actual MBP-1
   top-of-book per instrument — not assumed. This killed `btc_edge_v0` (9-tick BTC
   spread) and `level_scalp_v0` (adverse selection). The cost wall is computed here,
   per instrument, in Phase A — it is the first filter, not an afterthought.
4. **No look-ahead, ever.** Features see only data ≤ the decision timestamp. The Mira
   post-mortem (`mira_parity_audit_bench`) is the cautionary tale: feature-window ≤
   decision time, asserted at build.
5. **Cross-asset / options data is a FEATURE, never the trade.** Index futures, gamma
   walls, vol indices, related commodities, and the Polygon equity tape come in only as
   conditioning signals on a futures trade — we are not trading options here.

## Discipline (locked before results, btc_edge_v0 template)

- **HOLDOUT — SEALED.** Two tiers, because the tape lengths differ:
  - *Orderflow (MBP-1) edge tests:* the tape is only ~13 months (2025-05 → 2026-06),
    so seal the **last ~3 months** (≈ 2026-03-10 → 2026-06-09). Design/screen on
    2025-05 → 2026-03-09 only.
  - *Bar-only (1m, 2015→2026) edge tests:* seal the **last 12 months**
    (≈ 2025-06-10 → 2026-06-09), as in btc_edge_v0.
  - A finalist gets **one** pre-registered config tested on its holdout, logged
    win-or-lose here. The Phase-A **liquidity/cost scorecard is descriptive** (spread,
    depth, range) — not an edge test — so it samples the whole window; sealing applies
    only to edge claims in Phase C.
- **Two-regime consistency.** A candidate edge must hold with the **same sign in both
  halves** of the design window. Single-sample claims are rejected (the btc_edge_v0
  lesson: a full-sample "edge" was just drift wearing a trend filter).
- **Stressed costs.** Round-trip = measured spread + 1 tick slip + commission, charged
  per flip in price-relative terms. No frictionless numbers reported.
- **Multiple-comparisons honesty.** We screen many (instrument × family) cells; survivors
  must clear a bar that accounts for the number of cells tested, and get an independent
  adversarial review before any holdout shot.

## Data (all local — see docs/DATA_MANIFEST.md)

- **MBP-1 (L1 + trade tape), 31 symbols, ~2025-05 → 2026-06** — the honest-fill + cost
  engine. The instrument-economics scorecard (Phase A) is computed from this.
- **1m bars, 31 symbols, 2015 → 2026** — range / ATR / structure stats over deep history.
- **Cross-asset features:** index gamma walls (NDX/SPX/RUT/DJX), intraday option panels,
  vol indices (VIX/VXN/RVX/...), Polygon survivorship-clean US equities, and the other
  30 futures themselves (lead-lag).

Python: `C:\Users\benbr\BacktestStation\backend\.venv\Scripts\python.exe`.
Loaders: `data_io.py` (repo root) — `load_mbp1`, `load_futures`, `load_walls`, ...

## Layout

- `report/FEASIBILITY.md` — Phase A output: per-instrument tradeability scorecard + ranking.
- `report/OPPORTUNITY_MAP.md` — Phase B: cross-asset/options correlations to the shortlist.
- `out/scorecard.parquet` — the raw per-instrument metrics.
- `_scratch/` — disposable analysis scripts (gitignored).

## Status

- [x] **Phase A — instrument feasibility scorecard** (2026-06-20). Cost wall + range-vs-budget per
  instrument from MBP-1. Best non-index econ = CL/NG (+ marginal MBT/ZS); index dominates liquidity.
  See `report/FEASIBILITY.md`.
- [x] **Phase B — cross-asset opportunity map** (2026-06-20). **Cross-asset directional LEAD thesis =
  NULL** (no t-1 predictor for any instrument; all strong corrs contemporaneous). See `report/OPPORTUNITY_MAP.md`.
- [x] **Phase C — honest vol-gated ORB build** (2026-06-20). Engine (`orb_engine.py`) + sweep
  (`sweep.py`), self-tested, MBP-1 fill-verified, look-ahead-clean. Design survivors on ES/RTY/CL
  (NG dead). Verification GO on ES only; **holdout shot = NULL (outlier-driven, not deployable)** —
  see `report/VERIFICATION.md` + `report/HOLDOUT_LOG.md`.
- [x] **Phase D — day-flat family bake-off** (2026-06-20). 5 pre-registered families (gap-fade,
  gap-cont, VWAP-revert, afternoon-trend, pre-RTH-break) × 6 instruments, outlier-robust survivor rule.
  RTY gap-fade was the sole design survivor and passed all on-merits verification, but **walk-forward
  re-validation = NULL** (selection unstable, OOS inconsistent, pooled OOS outlier-driven /
  ex-top-2% negative). See `report/WALKFORWARD.md`.
- **FINAL VERDICT: no robust, OOS-validated, deployable day-flat edge** across ORB + 5 families × 6
  instruments. The binding fact: the lab's one robust edge (energy-RV, Sharpe +1.44) is multi-day,
  disallowed by the universal prop flat-by-close rule. Durable assets = `orb_engine.py`, `families.py`,
  `sweep.py`/`screen_families.py`, `walkforward.py`, MBP-1 fill verification, and the discipline.
