# unified_v0 — LEDGER

The "one brain, different hands" line: one continuation scorer for any upside thrust (earnings gap
OR breakout), on the **survivorship-clean Polygon universe** (delisted included, 2022-2026).

## Data foundation
- `D:\data\processed\stocks\polygon\daily_*.parquet` — grouped-daily, every ticker incl delisted,
  2021-06..2026-06, split-adjusted. 8,348 common stocks, 13.8M rows. (`data/pull_polygon.py`)
- `out/setups.parquet` — 235,502 upside thrusts (gap>=3% OR 20d-high breakout) with ~18 causal
  features + market-relative forward continuation x20/x40. (`build_setups.py`)
- `D:\data\processed\stocks\polygon\minute\` — entry-day 1-min bars for an 18k breakout sample
  (12k active + 6k delisted), incl DELISTED names (Polygon retains delisted minute history).
  5.56M bars, 0 errors. (`data/pull_polygon_minute.py`) Manifest: `minute_sample_manifest.parquet`.

## Findings

### 1. Unified daily continuation model (`run_unified_model.py`) — breakout/gap CONTINUATION is negative
Walk-forward LightGBM, x20 market-relative target, OOS 200k setups.
- rank-IC +0.100 (clean shuffled control +0.011; beats rel-strength-only +0.037).
- BUT the signal is almost ALL on the AVOID side: bottom decile -9.9%, **top decile -0.34% (20d),
  -0.61% (40d), -0.36% up-regime only** — even the best-scored thrusts revert market-relative.
- Drivers: regime (spy_ret60), size/liquidity, momentum. Setup-TYPE (gap vs breakout) barely matters.
- VERDICT: as a continuation strategy, thrust-triggered entries don't produce a positive long edge;
  the model's value is a **blow-up filter** (the -9.9% bottom decile). The momentum that works is
  CONTINUOUS relative strength (see `../run_asset_strength.py`, rank-IC +0.059), not triggered breakouts.

### 2. Intraday breakout entry (`run_intraday_entry.py`) — KILLED (2026-06-19, workflow wf_6ac66801)
The daily test used a wide daily-low stop. Re-tested R-geometry: 1-min entry AT the 20d-high cross +
TIGHT (1xATR) stop + let-run. Caught + fixed 2 look-aheads first (stop now uses ATR[i-1] not ATR[i];
minute reconciled to the OPEN). Raw result LOOKED good: meanR +0.185 ALL / +0.123 DELISTED, win 30.6%.
**5-agent adversarial verification: 2 killed, 3 weakened, 0 survives.** The +0.185R is REAL but NOT an edge:
- **NULL CONTROL = the kill (agent A):** breakout DAY-SELECTION is value-NEGATIVE. Same daily mechanic,
  breakout days -0.127R vs random non-breakout days +0.092R (same tickers) -> **delta -0.219R, name-block
  CI [-0.309,-0.130], 100% of draws <=0, negative every year.** Within-day control: level-cross +0.185 vs
  random-minute +0.018 -> the apparent edge is generic intraday-momentum + tight-stop GEOMETRY, NOT the breakout.
- **COSTS (agent C):** breakeven friction ~0.29%/side; at a realistic 0.30%/side meanR = -0.0125. The
  tradeable tier (>=$10, top-dvol quartiles) is ZERO-to-negative (Q4 most-liquid = +0.000); the only positive
  cell is untradeable sub-$10 thin names (median dvol $4.8M). 24.6% of entries gap over the level -> ~0R.
- **BREADTH/TAIL (B,D,E):** top 1% of trades = 68-82% of total R; ~0.5% of trades = 50% of R; equal-weight
  by ticker = +0.026 (median ticker -0.34R, only 40% of names profitable); drop top 5% -> NEGATIVE. A
  fat-tail lottery, not a broad edge. Honest cap [-2R,+6R] halves it to +0.096.
- NOT to blame (honesty): no look-ahead leak (clean audit); not survivorship; ATR-denominator REFUTED
  (ATR floor RAISES meanR to +0.215); +93/-149R were split-adjustment artifacts that NET -111R (a drag);
  independent from-scratch reimpl reproduced the stored parquet BYTE-FOR-BYTE (mean|dR|=0.0). The code is
  correct; the strategy is dead.

### 3. Strict HTF ladder — the real PDF setup, intraday (`build_htf_candidates.py` + `run_htf_intraday.py`, 2026-06-19)
GPT (correctly) noted our intraday test #2 used the BROAD 20d-high break, not the real high-tight-flag.
Ben wanted to keep trying breakouts -> ported momentum_trend_v0's full filter stack (prior thrust + tight
low-vol base + breakout-vol + MA align + not-extended + closes-near-HOD + narrow-range + linearity R^2)
onto clean Polygon. Ladder: LOOSE 5,924 / MID 833 / STRICT 62 (median dvol $26M, more liquid than broad).
- Intraday R LOOKS great (LOOSE +0.448 CI[+0.38,+0.52], STRICT +0.431) — but that's the SAME geometry/fat-tail
  illusion (intraday-momentum cross + tight stop), already debunked in #2. STRICT n=59 -> CI[-0.25,+1.22] (no power).
- DECISIVE NULL CONTROL (HTF day vs RANDOM non-HTF day, same ticker, identical daily mechanic): **NEGATIVE at
  every tier.** LOOSE HTF -0.217 vs random +0.138 -> **DELTA -0.356, CI[-0.457,-0.241] (entirely <0)**; MID
  delta -0.253; STRICT delta -0.630 (CI[-1.72,+0.32], underpowered). **Strictness does NOT help** — no
  monotonic move toward positive selection; the HTF breakout day is a WORSE entry than a random day in the
  same stock. STRICT can't be individually nailed (only 62 in 4yr; powering it needs pre-2021 data we don't
  have), but LOOSE (well-powered) + MID + the non-improving ladder = dead.
- BONUS (reinforces the survivor): random-day > HTF-day means **holding the strong stock beats timing its
  breakout** — literally the relative-strength conclusion.

### 4. Dedicated breakout SELECTOR w/ NEW free features — STILL dead (2026-06-19, Ben: "breakout selector anyway")
After the kill, Ben wanted a dedicated breakout selector w/ different features. Probed the $29 Polygon sub:
short interest + days-to-cover + short-volume ratio (squeeze), news count (catalyst), market-cap/float/SIC
(active-only) ALL FREE incl delisted (news/SI/SV). So built it at $0 extra. `probe_features.py`,
`pull_selector_features.py` (SI+SV per ticker), `pull_news_counts.py` (5d article count/setup),
`run_breakout_selector.py` (walk-forward LightGBM, base 18 + squeeze + news, judged vs random-day).
- Squeeze + news ADD NOTHING: rank-IC base +0.158 -> base+squeeze+news +0.143 (slightly WORSE = noise);
  importance days_to_cover #9, news_5d DEAD LAST #19/19. shuffled control ~0.
- DECISIVE null control: enriched top-decile breakout days -0.242 vs random days -0.088 -> **DELTA -0.154
  (still negative).** Even the fully-equipped selector's BEST breakouts < a random day in the same stock.
- News nudged the delta -0.196->-0.154 (catalyst breakouts slightly less-bad) = a faint echo of the EARNINGS
  edge, NOT a technical-breakout rescue. Top-decile intraday R looks +0.51 but base-only is HIGHER (+0.54)
  and it's the same geometry illusion.
- => EVERY feature family thrown at breakouts (momentum/structure/RS/regime/liquidity/size/short-interest/
  days-to-cover/short-volume/news) and the breakout day is ALWAYS worse than random. No selector exists.

## VERDICT: the BREAKOUT / HTF-momentum line is comprehensively CLOSED
- Daily continuation reverts (test 1); daily R-geometry breakeven (earlier momentum_trend_v0 work);
  intraday R-geometry = negative selection + costs-killed fat-tail lottery (test 2). Tested at every level.
- What SURVIVES: continuous cross-sectional RELATIVE STRENGTH (`../run_asset_strength.py`, rank-IC +0.059,
  long-short +4.26%/mo) — NOT triggered breakouts. Plus the unified model as a blow-up filter (test 1).
- Earnings gap line is separate, fragile-but-real (see `../earnings_gap_v0/LEDGER.md`).

### 5. Relative-strength long book (`run_rs_portfolio.py`, 2026-06-19) — REAL factor, MEDIOCRE naive standalone
Turned the confirmed RS signal into a real strategy: 12-1mo momentum, monthly rebalance, hold strongest
equal-weight, clean Polygon (delisted captured honestly), cost 0.1%/side, vs SPY B&H. 2022-2026 (~4yr).
- TOP DECILE: CAGR +20.3% / vol 24% / Sharpe 0.88 / maxDD -24% / Calmar 0.84 / **alpha +5.0%/yr**.
  TOP-50: +19.4%/Sharpe 0.69/Calmar 0.52/alpha +6.9%. SPY B&H: +16.3% / vol 16% / **Sharpe 1.03 / Calmar 1.23**.
- VERDICT: RS has positive alpha (beats SPY on RAW return) but at MUCH higher vol/DD -> **risk-adjusted it does
  NOT beat SPY** (lower Sharpe AND Calmar). More return, more risk; net worse per unit risk over this window.
- FRAGILE/LUMPY: alpha concentrated in 2022 (+26% excess, momentum's defensive year) + partial-2026 (+33%
  excess, +42.8% in 6mo CARRIES the CAGR); LAGS SPY in 2023 (-16%), 2024 (-5%), 2025 (-12%). 4yr w/ 1 partial
  year carrying it = don't trust it yet (factor is decades-robust academically; our window is just short).
- Turnover BRUTAL (690-880%/yr) -> cost-sensitive (thin alpha erodes at realistic 0.2%/side). SPY-trend
  filter (10mo MA) BACKFIRED (+2.4% CAGR, whipsaw) -> dead overlay.
- IMPROVEMENT PATH (untested): cut turnover (quarterly rebalance + ranking-buffer hysteresis), inverse-vol
  weighting (classic Sharpe lift), blow-up filter (unified-model bottom decile), momentum-native crash guard.

### 5b. RS book IMPROVED + adversarially verified (`run_rs_improved.py`, 2026-06-19) — clean build, UNPROVEN edge
GPT review (grounded in our numbers) -> built the research plan. WINNER = residual(beta-neutral) momentum / residual
vol + inverse-vol63 weights + 3% cap + rank-buffer(enter top10%/exit top40%) + NO beta hedge. Deployable @10bps:
CAGR +20.6%, vol 17%, Sharpe 1.22, maxDD -10%, Calmar 2.14, alpha +3.7% vs SPY; @50bps Sharpe 1.13. Beats SPY
(1.03/1.23) + MTUM (1.10/1.88) on raw metrics; EX-2026 holds (1.19). vol-mgmt+residual delivered as literature
predicts (vol 24->17, DD 24->10, Sharpe 0.88->1.22). GPT's beta-hedge bet (0.5-0.75) WRONG in-window (hedging hurt
in the bull; kept natural beta). **4-agent verification (wf_94c91023): 1 survives / 2 weakened / 1 KILLED.**
- A (leak+reimpl) SURVIVES: reproduces to machine precision (max diff 1.4e-17), NO look-ahead, delisting honest
  (52 dying held names ate real death-month losses incl FORD -36.6%; eventually-delisted = +6.7% of gross, net+
  only via M&A premiums = realistic). Liquidity fine (0% sub-$5; tightening to $20px/$50M-dvol IMPROVES to 1.37).
  No leverage (gross=1.0). Survives costs to ~75bps (breaks ~85-90bps). The BUILD is clean.
- BUT the CLAIM "beats SPY+MTUM risk-adjusted" does NOT survive: **alpha vs SPY statistically ZERO (NW t~0.3-0.5,
  p~0.6-0.8); P(book Sharpe>SPY)~0.45-0.58 = COIN FLIP; ties MTUM (excess -1%/yr).** ~100% of the excess is 2022
  (drop 2022 -> Sharpe<SPY, NEGATIVE alpha). KNIFE-EDGE on the 252d residual window (200d->1.01, 126d->0.68);
  drop-best-quarter -> 0.88. GOOD properties: NOT QQQ/tech beta (realized corr NEGATIVE), NOT concentrated (169
  effective bets), genuine breadth (~235 names), LOW/neg market correlation = attractive DIVERSIFIER profile.
- VERDICT: a cleanly-built, broad, low-market-corr momentum book — but on 4yr (1 partial) the edge is a 2022-
  concentrated, window-dependent, statistically-insignificant coin-flip. NOT deployable as "beats SPY" yet.
  THE decisive test = more history (esp. survive the 2020 momentum crash). DATA: ThetaData already has 2016+
  daily+minute incl DELISTED (covers 2018+2020 crashes); Polygon current floor ~2022-06 (needs upgrade for older).

### 5c. DECISIVE 9-YEAR TEST (2026-06-19) — RS edge was a SHORT-SAMPLE MIRAGE
Ben upgraded Polygon to Developer (10yr, ~$79 1-month); pulled clean 2016-07->2026 (`data/pull_polygon_deep.py`;
caught+fixed a 2-writer race first; integrity verified: 0 dupes, smooth split-adj boundary, benchmarks present).
Re-ran the book on **107 months (2017-07..2026-05)**:
- Deployable (residual/rvol+invvol+cap+buffer, no hedge): @10bps Sharpe **0.84**, Calmar 0.66, alpha +0.7%;
  @50bps Sharpe 0.76, alpha NEGATIVE. **SPY Sharpe 0.87, MTUM 0.86, QQQ 1.06.** Book TIES/slightly-LOSES to SPY.
- **Significance: mean excess vs SPY +0.73%/yr, Newey-West t = +0.15 (ZERO); beats SPY in only 44% of months.**
  The 4yr Sharpe 1.22 was a 2022-2026 regime artifact — exactly the coin-flip the verification predicted.
- BY-YEAR tells the regime story: GREAT in crashes (2020 +15.2% / 2022 +19.5% excess) but CRUSHED in junk/beta
  rallies (**2021 -30.4%** excess killed the alpha; 2019 -9.6, 2023 -10.2). corr(book,SPY) = **-0.14**.
- VERDICT: RS momentum is NOT a standalone edge here (alpha ~0 over 9yr). It IS a genuine CRASH-DEFENSIVE
  DIVERSIFIER (negative market corr, wins exactly when the market loses) — portfolio value, not alpha.
  Discipline win: almost believed 1.22; verification flagged coin-flip; 9yr confirmed wash. Durable asset =
  clean 9yr delisted-incl dataset (now supercharges EARNINGS validation + the squeeze/news selector features).

## EQUITIES SCORECARD (2026-06-19): breakouts DEAD | RS momentum = diversifier-not-alpha | EARNINGS = the one real edge

## Open / next
- RS book: try the improvement path OR accept "naive RS ~= SPY risk-adjusted" and focus earnings (the clear edge).
- Pivot momentum effort to continuous relative strength (the thing that actually works), not breakouts.
- Rotate the Polygon API key (throwaway sub).
- The clean minute infra (`data/pull_polygon_minute.py`, delisted-incl) + the verification harness are durable assets.
