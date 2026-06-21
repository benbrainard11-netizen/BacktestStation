# SPEC — earnings_gap_v0 constitution

Binding. Tests that violate this don't count. Mechanical, testable translation of the
source doc (see README). Shares the execution shell with
[../momentum_trend_v0](../momentum_trend_v0/SPEC.md) — only the setup detector differs.

## 0. Open decisions (resolve before Phase 1)

1. **Earnings-date source.** `yfinance` (free, installed) vs. a paid/vendor calendar.
   yfinance earnings dates can be incomplete/revised — audit coverage on our 133 names
   first. **Default assumed: yfinance for v0, flag coverage holes.**
2. **Premarket.** Define the gap from RTH open vs. prior close/high (works on current
   data) vs. re-pull extended hours to get true premarket gap + premarket volume.
   **Default assumed: RTH-open gap for v0; premarket criteria deferred to a re-pull.**
3. **Universe + survivorship.** Same as the trend strategy (§0.2/0.3 there). Earnings gaps
   occur on large caps, so NDX-100 is a less-biased first pass here.

## 1. Hypothesis

A long-based stock that gaps up > 7.5% above resistance on an earnings beat with strong
volume continues higher often enough that a ~40%-win, 3:1-R swing system has **positive
realized expectancy after honest fills, costs, and a regime filter** — and a model that
separates continuation gaps from fade gaps improves it.

## 2. Universe, windows, economics

- Universe per §0.3 (default 133 local NDX-100). Bars: daily for base/gap context, 1-min
  (RTH) for the intraday entry.
- **Dev: 2023-06-01 → 2025-09-30. Sealed holdout: 2025-10-01 → 2026-06-12.** Holdout budget
  2 lifetime reads (HOLDOUT_LEDGER.md), primaries registered before read #1.
- Economics: $0.005/share commission, slippage/spread per §7, long-only. Account $1k–$10k.

## 3. Setup detection (earnings gap-up; all features causal, ≤ decision time)

On an **earnings day** D for a name, it is a candidate gap-up if ALL hold (defaults
**bold**, alternatives are *registered secondaries* swept only under walk-forward §8):

1. **Earnings event on D** (from the §0.1 calendar; the beat itself is the catalyst — we do
   not need the EPS surprise number for v0, the gap is the proxy, but surprise is a
   registered feature if the source has it).
2. **Gap up** ≥ `gap_min` (**7.5%**): `open_D / close_{D-1} − 1 ≥ 0.075`
   (premarket gap once §0.2 re-pull lands).
3. **Open > prior-day high:** `open_D > high_{D-1}` (gap clears the prior range).
4. **Gap clears resistance, not into it.** `open_D` above the recent base's resistance band
   (e.g. max high over trailing `base_lookback` **60d**, minus a `res_buf`); reject gaps
   that open *into* overhead supply. Registered definition of "resistance."
5. **Long prior base.** Sideways for ≥ `base_min` (**>20** trading days; examples weeks–
   months): trailing range-bound + low trend slope before D.
6. **Volume.** Open/first-30-min volume ≥ `rvol_min` (**1.5–2×**) the trailing average
   (premarket volume added with the §0.2 re-pull).
7. **Liquidity.** Dollar-volume ≥ `liq_min` (registered) so fills are realistic.

## 4. Entry, stop (shared shell)

- **Intraday entry:** after the open, let the **first 1-min candle** form; enter when a
  later 1-min candle **trades through the first candle's high**; fill at that high + slip.
  Same logic on 5-min / 1-hour. (Identical to the trend strategy.)
- **Stop:** **low of day** of the entry day; clear it by `stop_buf` (**2–4 ticks**) per the
  honest-fill rule, don't sit on it.
- "Is my entry chasing?" — record entry distance above open / above trigger as a feature
  (the doc's risk-calculator chase check).

## 5. Risk + sizing (shared shell)

- Per-trade risk **1%** (0.5% poor regime, 2% max). `shares = floor(r·equity/(entry−stop))`.
- Position cap ≤ **30%** equity exposure (gap-down protection). Daily/concurrent caps
  registered.

## 6. Management, regime, and the model (shared shell + the earnings-specific model)

- **Scale-out:** sell **1/2** (alt 1/3) into strength at day **+3 to +5**, then **stop →
  breakeven** (p08 MRAM annotation).
- **Trail / exit:** exit the runner on a candle **close below MA10 (alt MA20)** (p08).
- **Regime filter:** the doc says "works best in stronger market cycles" → reuse the trend
  strategy's SPY/QQQ MA10/20 regime gate (and the cycle model, §6.5 there). New entries
  gated to risk-on regime; risk dialed by regime.
- **The model — gap continuation / quality (the "avoid the bad gaps" judgment).**
  Learn `P(gap continues to a target R over N days | gap features)`: gap size, gap-vs-
  resistance distance, base length/tightness, rel-volume, sector/market regime, prior
  trend, (EPS surprise + premarket if available). Replaces the binary §3 checklist with a
  calibrated quality score driving an EV/threshold trade layer. Shares the
  strength/weakness + cycle/rotation models with the trend strategy (umbrella §6.5).
  Discipline: realized-R objective, shuffled-target control, no-lookahead asserts, and it
  must beat the simple §3 rule on dev-OOS across periods or we keep the simple rule.

## 7. Honest fills + costs (CLAUDE.md §8)

Entry at the 1-min trigger + slip; stop exits honor gap-throughs (fill at open if it gaps
below the stop). **Stop-vs-target ties: stop wins.** Commission both sides; record
`fill_confidence`. Bar-level realized R must converge under finer-grained re-fill before
belief. NOTE: gap-day opens are wide/volatile → slippage stress is especially important.

## 8. Controls + discipline (same as the trend strategy SPEC §8, summarized)

1. No lookahead, asserted at build time (earnings date known only after the event; use the
   gap day's open onward, never the post-event drift to label the entry).
2. **Floor first:** beat (a) buy-and-hold the same names and (b) a naive "buy any earnings
   gap > 7.5%, stop LOD" baseline. The model must beat the simple §3 rule.
3. Parameter discipline: lock **bold** defaults; sweep alternatives only as registered
   secondaries under purged walk-forward; per-fold mean R, not pooled.
4. Walk-forward, embargo ≥ max hold; mandatory shuffled-target control.
5. **Frequency honesty:** this is a low-frequency setup — report the setup count; a handful
   of gaps on NDX-100 is not a statistic. This is the strongest reason to broaden universe.
6. Survivorship + universe + earnings-coverage disclosed on every result.
7. Realized R / equity curve is the objective; separately check the 40%-win / 3:1 claim.
8. Diagnose, don't declare; one revision cycle per construction, then verdict locks.

## 9. Phases

- **Phase 0 — data:** earnings calendar (§0.1) + audit coverage; SPY/QQQ; optional
  premarket re-pull (§0.2); broader universe if chosen. Causal loaders.
- **Phase 1 — detect:** earnings-gap detector (§3); count setups per period; eyeball vs.
  the doc examples (MRAM/PERI/ENPH/WOLF/TEAM/AMBA).
- **Phase 2 — backtest floor:** shared shell (entry/stop/partial/BE/trail/sizing/fills);
  realized-R + equity vs. §8.2 baselines, walk-forward.
- **Phase 3 — model:** gap-continuation model (§6) ablated vs. the simple rule; EV layer;
  reproduce-the-claimed-stats check.
- **Phase 4 — universe + holdout:** broaden, then the sealed holdout read. Final verdict.
