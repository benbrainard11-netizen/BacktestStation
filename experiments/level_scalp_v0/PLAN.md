# level_scalp_v0 — locked plan (v0.2, 2026-06-11)

v0.1 was adversarially reviewed by a 3-lens critique (leakage / microstructure /
statistics — see [report/plan_review_2026-06-11.md](report/plan_review_2026-06-11.md));
v0.2 folds in every blocker/major fix. **Spec freeze:** at the first atlas run, the touch
constants (2-tick band, 15-min cooldown, 60s approach window), the primary-cell list, and
the fill rules are frozen. Changing any of them afterward spawns a successor module that
may only be judged on NEW calendar data (post-2026-06-09) — never on this holdout.

Scope: ES/NQ/YM/RTY futures. Phased, kill-gated. No model until an ungated baseline is positive.

## Windows + holdout budget

| window | range | use |
|---|---|---|
| SELECTION | 2025-05-01 → 2025-12-31 | Phase 0 atlas ranking; Phase 1 Mode B config selection |
| CONFIRMATION | 2026-01-01 → 2026-03-31 (= the MBO window) | Phase 1 confirmation pass + the queue model; opened only after cells+configs are pinned in a committed manifest |
| HOLDOUT | 2026-04-01 → 2026-06-09 | **2 reads total for this module's lifetime**: (1) frozen ungated baseline after Phase 1, (2) frozen gated config after Phase 2 |

Holdout discipline: a config is "frozen" only when its full param manifest + git SHA are
committed BEFORE any holdout row is read. Every read is logged in `holdout_ledger.md`
(win or lose) before the next freeze is allowed. Both shots spent → module dead.
**Pre-specified holdout decision rule:** judged on the POOLED trade stream of the
pre-registered portfolio (fixed weights), not per cell. PASS = pooled mean > 0 at
day-block p20 AND inside the dev estimate's 90% CI. Per-cell holdout numbers are
descriptive only — ~48 days cannot adjudicate single cells.

## Non-negotiables A — level & feature legality

1. **Every level instance carries `(level_id, family, price_or_zone, valid_from_ts, contract)`.**
   The touch builder asserts `touch_onset_ts >= valid_from_ts` and refuses to emit otherwise
   — same build-time-assert pattern as rule 5, extended from features to level *existence*.
2. **valid_from per family is pinned in the Phase 0 table below.** Session-extreme levels
   (overnight/premarket/asia/london H/L) are NOT touchable during the session that defines
   them — the final extreme is by construction the most extreme touch (anchor-on-extreme).
3. **Dynamic levels (VWAP, σ-bands) are frozen at the last COMPLETED 1m bar before t0**;
   the frozen value carries its own `feature_window_end_ts` under the rule-5 assert.
   Half-back = prior-day RTH midpoint (static) only; developing-range variants banned in v0.
   `first/Nth touch` and `level age` are N/A for dynamic families (do not feed to Phase 2).
4. **MBO-defined levels (depth clusters / icebergs):** each instance carries `ts_define` =
   end of its defining-evidence window, built only from book/trade data `< ts_define`; only
   touches with `t0 > ts_define` count; the defining-evidence window must be disjoint from
   every counted touch's reaction window; defining executions are excluded from the touch
   sample and from Nth-touch counting. Mandatory placebo: the same selector run on prices
   offset by a random few ticks — if "reactions" persist, the construction is circular.
5. **Feature windows end at the DECISION timestamp** — `placement_ts` for maker,
   `trigger_ts − latency` for taker — never the touch. `feature_window_end_ts` recorded per
   row, asserted `<= decision_ts`; include a test that a deliberately mis-stamped row is
   rejected. (The Mira gate died on exactly this, hidden in reused plumbing.)
6. **Confluence at t0** counts only instances with `valid_from_ts <= t0`, values frozen
   pre-t0; emitted by the same builder that enforces rule 5. Negative test: an FVG forming
   after t0 must not change confluence at t0.
7. **Options timing:** prior-day chains only (OI publishes next morning); gamma-wall
   `valid_from` = 09:30 ET of session D (inherit `build_walls`' floor — NOT Globex open);
   source row strictly `date < D`, ≤7-day staleness; SPX→ES basis = prior-day 16:00 ET
   futures close − index spot, tick-snapped. Before any multi-year run on the new theta
   backfill: assert the vendor's OI date-stamp convention on 3 spot-check dates and record
   it in the dataset manifest.
8. **No roll-splice contamination:** roll-transition days excised from atlas and replay;
   builder asserts `level.contract == touch.contract` (.c.0 splices fabricate touches).
9. **Session-aware construction** (RTH/ETH windows via `app/research/sessions.py`); never
   naive UTC daily resamples.

## Non-negotiables B — fill honesty

10. **Touch detection on MBP-1 mid; FILL determination on trade prints + opposite-side
    quote.** A buy limit at L is filled iff a trade prints strictly through L OR the ask
    crosses to ≤ L. Same-side quote departure (bid leaves L via cancels) is NEVER a fill.
11. **Maker fill bracket — three rules, always reported together:** lower bound =
    trade-through/opposite-cross (rule 10); queue model = the *behind-you rule* on MBO (my
    order fills when any fill prints at L for an order_id whose add came after my
    placement — robust to invisible GTC depth and iceberg reserve); upper bound =
    visible-queue-volume (optimistic, reported only to size the gap). Headline = queue
    model where powered (rule 21), else lower bound. Never the upper bound.
12. **Book warm-up:** the clean MBO trading-day files start mid-stream with NO snapshot
    (verified: fills on order_ids never added in-file). Queue state must be seeded from the
    raw UTC-date MBO partitions (which contain the pre-open build) or by chaining prior
    trading-day files for multi-day levels; assert the book is seeded before the first
    queue estimate. Until that exists, the queue-model headline is restricted to levels
    created intraday after file start — and the report says so.
13. **Full order lifecycle on the raw tick stream** (never the deduped touch list):
    marketability check at placement (price already through level → reject or tag
    fill-at-market), first qualifying fill consumes the order, explicit cancel/re-arm
    policy per level, ETH resting either auto-cancelled outside RTH or evaluated against
    separately-measured ETH spread walls. Fills-per-placement reported so the adverse-
    selection denominator includes placements never touched.
14. **Placement is causal:** proximity trigger — place when mid first comes within P ticks
    of the level, P ∈ {at-creation, 16, 8, 4} — with `placement_ts >= valid_from_ts`
    asserted. "T seconds before touch" is an oracle policy (conditions on a future touch)
    and is allowed only as a clearly-labeled queue-value diagnostic, never a headline.
15. **Target exits obey the same bracket as entries** (long target fills iff bid ≥ target
    or trade through). Phase 0 reaction grids are measured on the EXIT-side quote (bid for
    longs), not mid — on NQ a 4-tick mid-bounce is not a 4-tick capture.
16. **Stops fill at the observed opposite-side quote at the first crossing event + latency**
    (not stop-price-plus-1-tick), with a stress ladder {+1, +2, +4} ticks and the realized
    slippage distribution reported per symbol. Stop-wins-ties; `fill_confidence`
    (exact/conservative/ambiguous) and `ambiguous_fill_count` per run (CLAUDE.md rule 8).
17. **Stops clear the level by 2–4 ticks** (stop AT the level = −0.6R / 90% stopped; 43% of
    winners retest the exact level within 2 ticks first).
18. **Costs in ticks, per symbol, measured** (§Cost walls). NQ taker results are reported
    at BOTH 1-tick and 2-tick slip (median NQ top-of-book = 2 lots; 1 tick is the base
    case there, not a stress).

## Non-negotiables C — inference

19. **Only pre-registered primary cells carry kill/advance authority** (table below).
    Everything else is exploratory atlas: reported with empirical-Bayes shrinkage toward
    the family×session mean, never gating. An exploratory cell can be promoted only by
    clearing the selection-aware p5 AND replicating on the confirmation window.
20. **Selection-aware bootstrap:** any "best of grid" statistic re-selects the max INSIDE
    each of the 1500 day-block resamples (reality-check logic — ~20-line change to
    `boot()`). Rankings use the selection-aware p5 lower bound of (edge − cost), never
    point ratios (winner's curse: max of noisy estimates ÷ constant).
21. **Min-n gate, power table first:** touch counts per cell are computed and published
    BEFORE reaction stats are unblinded. Ranking/gating requires n ≥ 200 touches AND ≥ 60
    distinct days (tier-3: ≥ 40 days, flagged). Below = "insufficient n" — not ranked, not
    killed, not advanced. Queue-model cells additionally need ≥ 100 dedup opportunities or
    only the lower bound is reportable (labeled "unpowered", not blank).
22. **Dedup by opportunity** `(symbol, level_id, touch_ts, side)` + a primary-family
    assignment for breadth claims: each physical touch belongs to exactly one family
    (pre-specified precedence); the family-overlap matrix is published; "cleared on k
    families" cites the deduped view only.
23. **Clustering:** day-block CIs resample CALENDAR days JOINTLY across symbols (one day
    index shared by all four books — ES/NQ/YM/RTY correlate ~0.9; 4 symbols ≈ 1.3
    effective replications, never 4 independent confirmations). Headline numbers must also
    survive a level-block (or 5-day-block) bootstrap, whichever is wider — prior-week
    H/L, walls and round numbers persist across days, so day blocks alone under-cover.
24. **Maker-vs-taker verdict only on the common 2026 window** (same touches, same days,
    paired difference-bootstrap). Mode B full-spine numbers are robustness, not the comparison.
25. **Label ≠ money:** everything judged on replayed net R.
26. **Phase 2 folds split on trading-day boundaries with a 1-trading-day embargo**
    (30m reaction windows otherwise leak across fold edges).
27. **Pipeline guards:** refuse 0-row caches; row-count guards per window; manifest
    (params + git SHA + row hash) on every cached dataset (mira_gate_harness skeleton).

## Pre-registered primary cells (LOCKED at first atlas run — Ben may amend before then)

One-time use of the leak-era family ranking to choose these; it is then dead as an input.
Primary reaction metric: P(revert k before through j) on the exit-side quote, at
(k,j) = (8,8) ticks for ES/YM/RTY and (12,12) for NQ (≈ spread-scaled equivalents).

| # | family | symbol | session | rationale |
|---|---|---|---|---|
| 1 | daily gap (gap_pdc) | ES | open (09:30–10:30 ET) | strongest leak-era family; gap-fill mechanism |
| 2 | premarket H/L | NQ | open | strongest leak-era per-trade |
| 3 | pdc (prior close, gap-magnet) | ES | on+pre | inventory-anchor mechanism; n≈565 (replaced prior-week H/L — unpowered everywhere, power_table_v0) |
| 4 | PDH/PDL | NQ | RTH | legal-construction prior; AM-only variant was under the n-gate |
| 5 | round numbers (100-handle) | NQ | RTH | whitespace, huge n; best-documented family (external research) |
| 6 | round numbers (25-handle) | ES | RTH | whitespace, huge n, ES = mean-reverter |
| 7 | wall-conditioned extremes: (pdh+pdl+onh+onl) × defend_sz_norm ≥ 2 | ES | RTH | the level × queue-state thesis as one pre-registered cell; n=530/137d verified |
| 8 | round numbers (10-handle) | RTY | RTH | n=952/138d; replaced VP POC (weakest external evidence) |

(2026-06-11 amendment, pre-unblinding: rows 3/4/7/8 swapped per power-table counts +
external research; VWAP bands and VP nodes demoted to exploratory families — tier-2
builders no longer block the first unblinding. Approved by Ben.)

## Graveyard (do not re-enter without a new mechanism)

- Naive fade-at-touch (−0.5R across families) — Mode A is admitted ONLY because the queue
  model + behind-you fill rule is a genuinely new mechanism.
- Take-liquidity sub-minute OFI scalps (move 0.3–0.4 ticks < spread; null everywhere).
- Gamma as regime/magnet/filter (5+ nulls). Walls as touch-levels only.
- Retrace-limit after confirmation (adverse selection, misses winners).
- Any model before a positive ungated baseline.

## Phase 0 — touch atlas (model-free, no trading)

**Touch:** MBP-1 mid within 2 ticks of level, onset-edge detection, 15-min cooldown that
keys off RAW onset times unconditionally (zone_events.py only arms the cooldown after a
label resolves — future-dependent sample selection; do not import that loop). Approach
direction from mid 60s pre-onset. Outcomes are THREE-way per (k,j): revert-first /
through-first / neither-within-horizon — "neither" stays in the denominator, scored at the
conservative time-stop value in kill math.

**Families & valid_from:**

| tier | family | valid_from |
|---|---|---|
| 1 | PDH/PDL, prior close/settle, prior-day half-back, prior-week H/L, prior-day VP (POC/VAH/VAL/HVN/LVN) | next Globex open (18:00 ET) |
| 1 | overnight H/L, premarket H/L | 09:30 ET |
| 1 | asia / london session H/L | that session's END |
| 1 | daily gap (needs rth_open), opening print | 09:30 ET |
| 1 | opening range H/L | 09:45 ET |
| 2 | round numbers | always (static) |
| 2 | session VWAP ±1/2σ | rolling — frozen at last completed 1m bar (rule 3) |
| 2 | FVG zones | third candle bucket-start + tf (its CLOSE — level_families.py stamps bucket-start, one bar early; fix on import) |
| 2 | equal H/L | second pivot's `knowable_ts_utc` from swing_pivot event_data (NOT `bar_end_utc` — hours-to-days early; fix on import) |
| 3 | gamma walls (call/put) | 09:30 ET session D (rule 7) |
| 3 | MBO depth clusters / iceberg refill prices | `ts_define` (rule 4) |

**Per-touch record:** pre-touch context (approach speed ticks/min, distance traveled,
time-of-day bucket, realized-vol regime, first/Nth touch where defined, level age where
defined, rule-6 confluence, spread at touch, **defending-side displayed size at onset —
raw + vs day median**: the universal at-touch wall feature, [MECHANISMS.md](MECHANISMS.md)
#2b) + the three-way reaction grid for
k,j ∈ {2,4,6,8,12,16} on exit-side quotes + MFE/MAE (ticks) at 1/5/15/30m + time-to-revert.

**Exploratory symbol sweep (no gating authority):** the wall/stop-cluster mechanism
families also run on the healthy-MBP-1 non-index complex (rates ZT/ZN/ZF/ZB, CL/NG, FX
majors, grains; metals excluded — mirror effectively empty; non-index MBO is 1 month, so
off-index walls are at-touch only). Every off-index cell carries a **capacity tag**
(typical defending size, trade rate): the prop copier trades ~20 accounts × 1–2 contracts
= 20–40 lots at one price — material in thin books. Off-index survivors must pass the
Phase 1 queue model at FLEET size, not 1 lot.

**Outputs:** `out/power_table.parquet` (published before unblinding), `out/atlas_touches_{sym}.parquet`,
`report/atlas_v0.md` — cells tagged **maker-viable / taker-viable / both / neither**
(evaluated against BOTH cost walls — the taker wall alone would pre-kill the maker thesis
on NQ, where taker ≈ 4.8 ticks but maker ≈ 1.8). Plus the **retest table**: conditional
retest rate within k ticks after first rejection, by family × overshoot × time-of-day
(the number the public literature doesn't have — external_research.md §upgrades #4).

**Advance/kill:** module advances iff ≥1 primary cell clears its wall at selection-aware
day-block p5 on SELECTION, or an exploratory cell clears AND replicates on CONFIRMATION.
No primary clears and no exploratory replicates → null report, park. That verdict is a success.

## Phase 1 — execution physics (on surviving cells)

Tick-by-tick quote+trade replay (extend `realized_r.load_mbp1` to read action/price/size).

**Mode A — maker:** proximity-triggered placement (rule 14), full lifecycle (rule 13),
3-rule fill bracket (rule 11), book warm-up (rule 12). Adverse selection measured directly:
E[reaction | filled] vs E[reaction | touched], denominators per rule 13 — the gap between
the two is the tax the fill model must overcome; strategies are judged on
**fill-conditioned PnL, never touch-conditioned**.
Queue model (external_research.md §upgrades, lit: Huang-Lehalle-Rosenbaum, Moallemi-Yuan):
**exact FIFO queue replay from MBO** — join the back of the displayed queue at effective
arrival (send time + sampled latency), advance only on cancels/fills ahead — with
**competing-risks outcomes** (fill / move-away-before-fill / through-without-full-fill /
cancel-race) at horizons {100ms, 500ms, 1s, 5s, 30s, 2min}, an explicit
**hidden-liquidity multiplier** on queue-ahead estimated from observed refill/iceberg
events, and cancel latency modeled. MBP-style probabilistic queue models (Rigtorp,
hftbacktest) are stress tests only. The T-before-touch event-aligned synthetic-order
study is the queue-value DIAGNOSTIC (legitimate as measurement, never as policy).

**Mode B — taker:** trigger = bid ≥ L + δ for longs (ask ≤ L − δ shorts) — the side you
hit, not mid flicker; fill at the first quote update at or after `trigger_ts + latency`;
latency ladder {0, 0.25, 1, 2, 5}s (the 250ms rung is where retail actually lives and
where NQ's 2-lot ask evaporates). Optional pre-DECISION flow filter (rule 5 naming).

**Exits (both modes):** fixed tick targets {4,6,8,10,12} scaled in spread-multiples for
NQ/YM × stop = level ∓ (2–4 tick buffer) × time-stop {5,15,30}m; fill rules per 15/16.

**Procedure:** config selection (Mode B) on SELECTION only; pin one headline config per
cell in a committed manifest; CONFIRMATION run = the one confirmatory pass (and the only
place the queue model exists); the 315-config grid appears solely as sensitivity curves on
SELECTION. Then holdout shot #1 on the pooled frozen portfolio.

**Kill:** no pinned config positive at p5 on CONFIRMATION → module NULL. Park, document.

## Phase 2 — conditioning (only on a positive confirmed baseline)

Pre-decision features only (rule 5); walk-forward LightGBM (`wf_gate` pattern) with
trading-day folds + embargo (rule 26); judged on replayed net R; random-feature negative
control mandatory; harness = mira_gate_harness skeleton. **Per-instrument refits** —
ES/NQ/YM/RTY share architecture, never coefficients. Then holdout shot #2.

## Phase 3 — money layer (already built)

`sizing_v1` (account.py + firm_rules + block-bootstrap MC) consumes the per-trade R
stream. Scalp shape (high win, low variance) fits prop trailing-DD rules best — but the
daily-loss limit binds harder at scalp frequency; check it first.
**Fleet-size fills:** the deployment shape is ~20 copied prop accounts × 1–2 contracts =
20–40 lots at one price. The Phase 1 queue model is therefore ALSO evaluated at fleet
size (fill probability + adverse selection for the 40th contract in the queue, not the
1st) before sizing_v1 multiplies anything by 20; thin-book symbols are capacity-capped.

## Cost walls (MEASURED on this repo's MBP-1 — RTH medians, 2025-09/2026-03/2026-05)

| sym | tick $ | spread (med RTH) | ToB depth | comm (ticks) | taker RT ≈ | maker RT ≈ |
|---|---|---|---|---|---|---|
| ES | 12.50 | 1 tick | deep | 0.30 | ~2.3 t | ~1.3 t |
| NQ | 5.00 | 3 ticks (p90 4–5) | ~2 lots | 0.76 | ~4.8 t (5.8 @2-tick slip) | ~1.8 t |
| YM | 5.00 | 2 ticks (p90 3) | ~3 lots | 0.76 | ~3.8 t | ~1.8 t |
| RTY | 5.00 | 2 ticks | ~3 lots | 0.76 | ~3.8 t | ~1.8 t |

Stressed convention: $3.80 RT commission; taker pays spread + 1 tick entry slip (NQ also
@2); stops per rule 16. **Target exits are NOT free**: a resting target fills only on
exit-side-quote-through (rule 15) ≈ one extra spread of required move — restate the wall
as the (entry-mode × exit-path) matrix in every report. ETH walls measured separately.
Routing claims (which symbol carries a family) require a difference-bootstrap (rule 23).

## Reuse map (import WITH the listed fixes — the leaks are in the reuse code verbatim)

| need | use | fix on import |
|---|---|---|
| data access | `backend/app/data/reader.py` | cache per (sym,day); fail loudly on empty reads |
| session math | `backend/app/research/sessions.py` | — |
| touch onset/OFI | `market_state/intraday/zone_events.py` (cks_ofi_inc), `events_v2.py` (vol-scaling) | cooldown keys off raw onsets (theirs is post-label = leaky); OFI window re-anchored to decision ts (theirs is [t0,t0+2s) = post-touch); do NOT import events_v2's after=0 onh/onl lines or day-static confluence |
| level schema | Mira `LevelSpec` shape (level_known_ts_utc) | levels.py's wide table has no timestamps — don't use it as schema |
| extra families | `experiments/mira_upgraded_v0/level_families.py` | FVG known-ts +1 bar (to candle CLOSE) |
| equal levels | `backend/app/research/detectors/equal_levels.py` | valid_from = second pivot's knowable_ts_utc |
| gamma walls | `mira_gate_harness/gamma_wall_levels_test.py:build_walls()` | keep its 09:30 floor; assert vendor OI convention on regen |
| quote replay | `mira_gate_harness/realized_r.py` | extend load_mbp1 to trades (action/price/size) |
| exit variants | `sizing_v1/exit_replay_oos.py:exits_for()` | target rule (bid≥target) sound; stop fill = observed quote, not flat −1R |
| CI ruler | `reclaim_entry.py:boot()` | add joint-symbol day draw + in-resample re-selection (rule 20/23) |
| association judge | `market_state/validation/harness.py:forward_test` | — |
| instrument constants | `backend/app/backtest/instruments.py:lookup()` | — |
| harness skeleton | `mira_gate_harness/harness.py` | manifest doubles as the holdout unblinding gate |
| money layer | `experiments/sizing_v1/` | ignore dead bs-mira-v15 paths |

## Priors (consumed, then dead)

The leak-era family ranking was used exactly once — to choose the primary cells above —
and is no longer an input; it may never justify post-null iteration. The AM PDH/PDL
+0.333R figure is UNTRUSTED (1m-bar construction, gross, no costs) — a sanity anchor at
best. The honest ungated Mira stream is negative (−0.22..−0.32R at 1–3R structural
geometry); this module's geometry differs, but the burden of proof is entirely on us.
**Post-null clause:** after a null, the answer is "measured, no edge at this spec" — not
"loosen the touch band". Successor specs get new calendar data only.
