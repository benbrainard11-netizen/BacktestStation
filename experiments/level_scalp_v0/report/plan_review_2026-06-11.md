# PLAN v0.1 adversarial review — 2026-06-11

Three independent critics (leakage / microstructure / statistics lenses) attacked PLAN
v0.1 before any code. All three returned "not sound as written, fixable". Every
blocker/major below is folded into PLAN v0.2; this file is the audit trail.

## Leakage lens — verdict: enforcement perimeter was wrong (features covered, level existence / selection / actions not)

| sev | finding | fix in v0.2 |
|---|---|---|
| BLOCKER | No per-level `valid_from_ts`: ON/premarket/session H/L touchable mid-formation (live bug: events_v2.py puts onh/onl in LINES with after=0; levels.py docstring claim false under full-day touches). Anchor-on-extreme inflation. | Rule A1 + per-family valid_from table |
| BLOCKER | equal_levels stamps the cluster at second pivot's bar_end (bucket-START) — hours-to-days before pivot confirmation (`knowable_ts_utc`). | valid_from = knowable_ts_utc (rule, reuse-map fix) |
| BLOCKER | Mode A "place T sec before touch" = oracle placement (conditions on future touch; queue position from oracle-chosen instant). Also: resting orders fill at cooldown-suppressed touches the sim would skip. | Proximity-trigger placement (rule B14); lifecycle on raw stream (B13) |
| BLOCKER | MBO depth/iceberg levels: persistence-selection and refill-evidence CONSUME touches — circular level selection that survives the feature-window assert. | ts_define discipline + evidence/touch disjointness + offset placebo (rule A4) |
| major | zone_events cooldown arms only after a label resolves → sample membership depends on the future; timeout touches vanish from denominators. | Raw-onset cooldown; three-way outcomes with "neither" kept (Phase 0 spec) |
| major | Confluence computed against the day's static level table credits levels that don't exist yet (events_v2 day_levels precedent). | Rule A6 |
| major | Dynamic levels (VWAP bands, half-back): partial-bar values, day-final vectorized paths, undefined identity/cooldown. | Freeze at last completed bar; half-back = prior-day mid only (rule A3) |
| major | Phase 0→1 same-window confirmation + unbounded "one shot per frozen config" = serial holdout mining (mira_gate precedent: the old holdout was hit a dozen+ times). | SELECTION/CONFIRMATION split; 2-shot lifetime budget; ledger |
| major | Gamma-wall validity floor unspecified for the multi-year regen; vendor OI date convention can silently flip prior-row→same-day. | Rule A7 |
| major | Reused OFI window is [t0, t0+2s) — post-touch; "pre-touch OFI filter" would be post-decision data. | Rule A5: windows end at DECISION ts |
| minor | FVG known-ts stamped at third candle bucket-start (1 bar early) in level_families.py AND fvg_formation.py. | +tf to candle close (reuse map) |
| minor | Phase 2 walk-forward needs day-boundary folds + embargo. | Rule C26 |

## Microstructure lens — verdict: two spec holes would reproduce the optimistic-fill error class

| sev | finding | fix in v0.2 |
|---|---|---|
| BLOCKER | Clean MBO trading-day files start mid-stream with NO book snapshot (verified on disk: fills on order_ids never added in-file); GTC depth at multi-day levels invisible → queue-ahead one-sidedly undercounted, worst exactly at PDH/round-number/wall levels on ES. | Book warm-up from raw UTC partitions / chained days; behind-you fill rule; 3-rule bracket (rules B11/B12) |
| BLOCKER | "Trades through ≥1 tick" is only a guaranteed-fill bound on TRADE prints or opposite-side quote; v0.1 rule 3 ("bid/ask/mid only") + quotes-only load_mbp1 pointed implementers at same-side quote-through, which is NOT a bound (pull-through via cancels). | Rule B10; extend load_mbp1 to trades |
| major | T-before-touch placement future-conditioned; lifecycle absent (marketable-at-placement undefined, one order filling multiple touches). | Rules B13/B14 |
| major | Target exits are resting limits with the same queue problem — v0.1 cost table booked them at 0 ticks; exits_for's bid≥target rule costs ~1 spread of extra adverse move (NQ: 4-tick target needs ~7 ticks of mid move). | Rule B15; grids on exit-side quote; cost matrix |
| major | Spread priors stale-optimistic vs this repo's own data: NQ median 3 ticks (mean 3.6, p90 4–5, ToB ~2 lots), YM 2 (p90 3). | Measured cost-wall table; NQ @2-tick slip |
| major | Stop fills modeled at stop+1 tick ignore gap-through in stop-run sweeps — first-order at 4–12 tick targets. | Rule B16 (observed quote + {1,2,4} stress) |
| minor | Taker-only kill wall pre-kills the maker thesis on NQ (taker ~4.8t vs maker ~1.8t). | Both walls, maker/taker-viable tags |
| minor | Mode B trigger series unpinned; ladder missing the 50–500ms band. | bid≥L+δ trigger; 250ms rung |
| minor | Queue-model cells unpowered on sparse families × 112 MBO days. | Rule C21 min-n; "unpowered" labeling |
| minor | .c.0 roll splices fabricate touches/trade-throughs (Mar+Jun 2026 rolls inside windows). | Rule A8 |

## Statistics lens — verdict: dev gates couldn't fire; everything funneled onto an underpowered, unboundedly-reusable holdout

| sev | finding | fix in v0.2 |
|---|---|---|
| BLOCKER | ~800 cells × max over 36–72 (k,j) sub-tests ≈ 30k estimates; max-statistic at naive p5 → 100–300 spurious survivors expected under a pure null; module-kill could never fire. | ≤8 pre-registered primary cells with gating authority; selection-aware (re-select-in-resample) bootstrap; shrinkage for exploratory cells (rules C19/C20) |
| BLOCKER | Phase 1 "confirmed" Phase-0 selections on the SAME dev data (+315 execution configs of fresh selection). | SELECTION/CONFIRMATION temporal split; one pinned config per cell before CONFIRMATION opens |
| BLOCKER | "One shot per frozen config" = unbounded config shopping (1−0.95^K); precedent: mira_gate's named holdout was evaluated by 8+ scripts. | 2-shot lifetime budget, manifest-before-unblinding, ledger, successors on new calendar only |
| major | Holdout underpowered per cell (~48 days; p5>0 needs observed ~+0.19R vs plausible +0.05–0.15R true edge) → false-kills real edges, fueling the shopping loop. No success criterion was stated. | Pooled pre-registered portfolio; PASS = pooled >0 at p20 AND inside dev 90% CI |
| major | No min-n gate: once-per-day families split 4 sessions × first/Nth → n≈45–115 (binomial SE ~7pp) ranked against n≈3000 round-number cells. | Rule C21 power-table-first + n≥200/days≥60 gate |
| major | Edge-to-cost point-ratio ranking = winner's curse (max of noisy estimates ÷ constant). | Rank by selection-aware p5 lower bound (rule C20) |
| major | Day-block bootstrap mis-specified: 4 correlated symbols/day ≈ 1.3 effective obs; persistent levels (prior-week, walls, round numbers) cluster across days. | Joint calendar-day draw + level-block robustness (rule C23) |
| major | Priors section invited motivated continuation (leak-era ranking as adaptive input; gross 1m-bar +0.333R framed as "best legal prior"; no post-null clause). | Ranking consumed once for primaries then dead; +0.333R relabeled untrusted; post-null clause + spec freeze |
| minor | Maker-vs-taker verdict confounded by non-overlapping windows (MBO=2026Q1 only). | Common-window paired comparison (rule C24) |
| minor | Confluent touches populate multiple family cells → breadth overstated. | Primary-family dedup + overlap matrix (rule C22) |

## Bugs found in EXISTING repo code during this review (fix forward, separately)

- `market_state/intraday/events_v2.py`: onh/onl/gap in LINES with `after=0` — touchable
  during formation; day-static confluence credits future levels.
- `market_state/intraday/levels.py`: docstring claims "each known by the time a touch
  could occur" — false under a full-Globex-day touch stream.
- `market_state/intraday/zone_events.py`: cooldown armed only on label resolution
  (future-dependent sample selection).
- `backend/app/research/detectors/equal_levels.py:152` — comment "when cluster is
  knowable" wrong; uses second pivot bar_end (bucket-start), not knowable_ts_utc.
- `experiments/mira_upgraded_v0/level_families.py:89` + `fvg_formation.py` — FVG known-ts
  at third-candle bucket-START (one bar early; harmless in mira_upgraded's pre-open usage,
  unsafe intraday).
