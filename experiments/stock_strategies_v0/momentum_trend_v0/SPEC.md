# SPEC — momentum_trend_v0 constitution

Binding. Tests that violate this don't count, in either direction. This is the
mechanical, testable translation of the discretionary source doc (see README). Where the
doc is discretionary, the mechanical definition is **a hypothesis to be tested**, not a
claim that it equals the author's eye — §0 and §6 track that gap.

## 0. Open decisions (resolve before Phase 1 — these change what we build)

1. **Research path.** (a) *Mechanical backtest* — fully mechanize and measure realized R
   on history (default; this is a backtesting lab). (b) *Candidate scanner* — mechanize
   only the objective filters, surface setups for human review, don't claim a backtested
   edge. (c) Both: scanner now, backtest as the validation. **Default assumed: (a).**
   **Direction (Ben, 2026-06-18): model the discretion** — the leadership/sector/cycle
   and the "5-star eyeball" judgments become learned models (§6.5), not hand-coded
   proxies. So the build is: mechanical execution shell (§3–§7) + ML for the discretion.
2. **Universe.** NDX-100 large caps (have it now) vs. a broader liquid-US pull (fairer to
   a 30–300%-mover strategy, needs a ThetaData stock pull + a liquidity/price screen).
   **Default assumed: start NDX-100 as a conservative first pass, flag undercoverage.**
3. **Survivorship.** Current NDX-100 membership ≠ historical → survivorship bias baked in.
   Acceptable for a first pass *if disclosed*; a clean test needs point-in-time membership.

## 1. Hypothesis

Stocks that thrust hard, base tightly into a rising 10/20-MA on declining volume, and
break out on expanding volume continue higher often enough that a ~30%-win, 3–4:1-R swing
system has **positive realized expectancy after honest fills, costs, and a regime filter**,
on a universe and in regimes where the setup actually occurs.

## 2. Universe, windows, economics

- Universe: per §0.2. Default = the 133 local NDX-100 names.
- Bars: daily (EOD) for setup/regime; 1-minute for the intraday entry refinement.
- **Dev window: 2023-06-01 → 2025-09-30.** **Sealed holdout: 2025-10-01 → 2026-06-12.**
  Holdout read budget: **2 lifetime reads**, logged in HOLDOUT_LEDGER.md, primaries
  registered here before read #1. Walk-forward inside dev is the everyday honesty check.
- Economics (equities): commission $0.005/share (cap-aware), spread/slippage modeled per
  §7, **short borrow N/A** (this is long-only). Account model $10k, sizing §5.

## 3. Setup detection (daily bars, all features causal: use only data ≤ day D)

A name is a candidate base on day D if ALL hold (param defaults in **bold**, registered;
alternatives are *registered secondaries*, swept only under §8 walk-forward):

1. **Prior thrust.** Max close-to-close run-up over a trailing window ≥ threshold.
   `thrust_pct` ∈ {**30%**, 100%, 300%} over `thrust_window` ≤ **60** trading days.
   (Three thrust tiers map to the doc's "30%+ … 100–300%".)
2. **Base / consolidation.** ≥ `base_min` (**3**) and typically more days after the thrust
   where: (a) price range-bound — base high/low spread ≤ `base_width` (**25%**) of base
   mid; (b) **declining volume** — mean base volume < mean thrust volume × `vol_dry`
   (**0.7**); (c) price hugs the MAs — close within `ma_hug` (**8%**) of the 10-day MA on a
   majority of base days. "Longer base better" → record `base_len` as a feature, don't cap.
3. **Narrow-range run-in.** The last `nr_days` (**3**) before breakout each have daily range
   < median base daily range (the doc's "series of narrow range days").
4. **MA alignment ("surfing").** On D: `close > MA10 > MA20`, MA10 and MA20 flat-to-rising,
   and price "respects" the MAs over the base (low ≥ MA20 on ≥ `respect_frac` (**0.7**) of
   base days).
5. **Not extended.** `(close − MA10)/MA10 ≤ extend_max` (**10%**) at the breakout.
6. **Linear, not "barcode".** Thrust-leg log-price regression R² ≥ `linearity_min`
   (**0.80**) AND base ATR%/price ≤ `chop_max` (**registered**); high day-to-day
   range volatility ("barcode") is excluded.
7. **Tradability / character screen** (the chart-header stats in every doc example —
   DIAGRAMS.md). `ADR%` (avg daily range %) ∈ a sane band (examples ran ~4–9%) — enough
   to move, not a barcode; **low float preferred** (`float ≤ float_max`; examples 11M–174M,
   mostly <200M). ADR%/ATR are bar-derived. **Data gap: float/shares-outstanding and
   earnings dates are NOT in OHLCV** → need a fundamentals + earnings-calendar source.
   No entries into earnings (gap risk; biotech especially, doc §4).

MA set (from the charts): **MA10/MA20 are the trade MAs**; MA50 (black) and EMA200 (red)
are context/trend filters available as features.

## 4. Breakout trigger + entry

- **Breakout day** B: close > base high (range top), **breakout volume > prior-day volume**
  (and ≥ base-avg × `bo_vol_mult` **1.5**), close near HOD: `(HOD−close)/(HOD−LOD) ≤ 0.25`.
- **Entry modes** (test both; they are different fill models):
  - **Daily mode (beginner):** enter next-session **open** after B (honest; entering on
    B's close requires the close, which isn't tradeable). Slippage per §7.
  - **Intraday refinement (1-min):** on B, let the **first 1-min candle** (09:30–09:31 ET)
    form; enter when a later 1-min candle **trades through the first candle's high**; fill
    at that high + slippage. Same logic available on 5-min / 1-hour. Stop = LOD of B.
- **Stop:** **low of day** of the entry day (doc rule). Stop must clear the LOD by
  `stop_buf` (**2–4 ticks / $0.01–0.05**) per the repo honest-fill lesson, not sit on it.

## 5. Risk + position sizing (rules, never model output)

- Per-trade risk `r` = **1%** equity (0.5% in poor regime §6, 2% max in strong regime).
  `shares = floor(r·equity / (entry − stop))`.
- Position caps: ≤ **30%** equity exposure (swing, gap-down protection) AND ≤ 50% absolute.
  `shares = min(shares, 0.30·equity/entry)`.
- Hard portfolio rules to encode: max concurrent positions, daily/weekly loss cap (optional,
  registered), no adds beyond the cap.

## 6. Trade management + regime + leadership

- **Scale-out:** sell `partial_frac` (**25–50%**) into strength on day **+3 to +5** after
  entry (registered: fixed day vs. extension-trigger; the AMR/HUT examples used 25–50%).
  Then **stop → breakeven**.
- **Trail:** exit the runner on the **first daily CLOSE below MA10** (alt MA20). Sharpened
  from the AMR/HUT annotations — it's close-below, not intrabar.
- **Re-entry (explicit doc rule, p08).** A stop-out does not retire a still-valid base:
  allow up to `max_attempts` (**registered**, e.g. 2–3) re-entries on the same setup while
  the breakout level/base structure holds. The backtest must model this (one base → ≥1
  entry attempt), and costs/risk apply per attempt.
- **Regime filter (needs SPY/QQQ — data gap; p14 QQQ COVID example):** no NEW entries when
  `MA10 < MA20` on SPY *or* QQQ; resume when MA10 crosses back above MA20; also stand aside
  while either index is ≥10% below its trailing-`63d` high. Risk per trade dialed by regime
  (poor/normal/strong) per §5. This is the simple rule; §6.5 may replace it with a model.
- **Sector / leadership — see §6.5 (modeled, not a hand-coded proxy).**

## 6.5 Modeling the discretion (Ben's direction — the real research)

The discretionary judgments become learned models, each trained causally (features ≤ t),
validated walk-forward (§8.4), and **ablated against the simple rule** so we know the model
earns its complexity. Three components:

1. **Strength/weakness model.** Cross-sectional relative-strength ranking of (a) sectors
   and (b) stocks within sector. Output: is this name a *leader* (top of its group) right
   now? Features: multi-horizon returns, relative volume, distance-from-highs, breadth of
   the sector group. Replaces the §6 "top-20% RS" proxy. Needs a sector/theme mapping
   (GICS or a clustering of the universe) + sector aggregates.
2. **Cycle / rotation model.** Where are we in the market cycle (the p15 diagram) and which
   sectors are *receiving* rotation (money flowing in). Output: cycle-phase / risk-on-off
   state + a sector-rotation signal. Subsumes the §6 regime filter. Features: index trend
   structure, breadth, cross-sector RS dispersion, vol regime. Start simple (the MA10/20
   gate is the floor it must beat), grow toward a phase classifier.
3. **Setup-quality model.** Learns the "5-star eyeball" score from the objective features
   (base length/tightness, volume dry-up ratio, ADR%/ATR, float, MA structure, linearity,
   distance-not-extended) → P(breakout follows through to a target R). Replaces the binary
   §3 checklist with a calibrated quality score; the EV/threshold trade layer uses it.

Discipline for all three: realized-R is the objective (§8.8), shuffled-target control
(§8.4), no-lookahead asserts (§8.1), and **the model must beat its simple-rule floor on
dev-OOS across multiple periods** or we keep the simple rule (§8.6 ablation). Sequence /
deep models only after the tabular versions are stable and positive.

## 7. Honest fills + costs (CLAUDE.md §8 applies)

- Intraday entry filled at the trigger price + `slip` (**1 tick / $0.01–0.02 or k·spread**);
  daily-mode entry at next open + slip. Stop exits: if the bar/day gaps through the stop,
  fill at the **open** (gap-down honored), else at stop − slip. **Stop-vs-target ties: stop
  wins.** Commission both sides. Record `fill_confidence` per the repo rule.
- Bar-level realized R must converge under a finer-grained re-fill before any number is
  believed (the repo's `fill_realism` discipline, adapted to equities 1-min).

## 8. Controls + discipline (each is a paid-for repo lesson)

1. **No lookahead, asserted at build time.** Setup/breakout/regime features use only data
   with timestamp ≤ decision time; intraday entry uses only ticks ≤ entry. Assert it.
2. **Geometry/regime floor first.** The strategy must beat (a) buy-and-hold the same names
   over the same windows, and (b) a naive "buy any 20-day-high breakout, stop LOD" baseline.
   A lift only over *no* baseline is not evidence.
3. **Parameter discipline.** Many knobs (§3–§6). Lock the **bold** defaults from the doc;
   sweep alternatives only as *registered secondaries* under purged walk-forward. Report
   per-fold mean R, not pooled; a config that only wins pooled or in one fold is noise.
4. **Walk-forward, no random splits.** Expanding-train, embargo ≥ max hold horizon; the
   mandatory shuffled-label negative control (abort if it shows edge). Day/name-block
   bootstrap for CIs (positions overlap in time and cluster by sector).
5. **Replication before belief.** Per-window noise is large for a ~30%-win system; need
   multi-period and (once universe expands) multi-cohort consistency. Single-window lifts
   presumed noise.
6. **Ablate the discretionary rules.** Report realized R with/without the leadership filter
   (§6) and with/without the regime filter, so we know which rules actually carry the edge
   vs. which are folklore.
7. **Survivorship + universe disclosed.** Every result states the universe, the membership
   basis (current vs. point-in-time), and the setup-occurrence count — a strategy that
   fires 4 times on NDX-100 has no statistics regardless of its R.
8. **Realized R / equity curve is the objective**, not win-rate or pattern-match accuracy.
   We separately check whether the author's 30%-win / 3–4:1-R / ~20%-DD profile reproduces.
9. **Pipeline guards.** Never cache 0 rows; assert in-window candidate counts > 0; every
   dataset/result carries a manifest (git SHA, params, source row hash).
10. **Diagnose, don't declare — verdicts lock.** Each negative names the failing component
    (setup def / breakout / entry / leadership / regime / fills / universe). One revision
    cycle per registered construction, then the verdict locks.

## 9. Phases

- **Phase 0 — data + gap close.** Confirm bar coverage; pull SPY/QQQ (regime); for the
  modeled path, pull/derive sector mapping + sector aggregates, a broader universe (§0.2),
  and a float/shares + earnings-calendar source (§3.7). Build causal loaders.
- **Phase 1 — mechanize + detect.** Setup detector (§3) + breakout (§4) on daily bars;
  count candidates per name/period; eyeball a sample vs. the doc's described pattern.
- **Phase 2 — backtest core (simple-rule floor).** Daily-mode entry, stop, scale-out
  (25–50%/BE), close-below-MA10 trail, re-entry, sizing, honest fills (§4–§7); realized-R
  + equity curve vs. the §8.2 baselines, walk-forward. Simple MA10/20 regime + top-RS
  leadership proxy — this is the floor the models must beat.
- **Phase 3 — model the discretion (§6.5).** Build the three models (strength/weakness,
  cycle/rotation, setup-quality), each **ablated against its Phase-2 simple-rule floor**;
  EV/threshold trade layer on the setup-quality probability. Then the intraday-entry fill
  model and the reproduce-the-claimed-stats check.
- **Phase 4 — universe expansion + holdout.** Broader universe (if §0.2), then the sealed
  holdout read (§2). Final verdict.
