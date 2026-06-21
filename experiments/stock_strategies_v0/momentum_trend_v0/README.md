# momentum_trend_v0 — High Tight Flag momentum swing strategy

Source: *Momentum Trend Following Strategy* (discord.gg/sartrading mentorship PDF,
`C:\Users\benbr\Downloads\Momentum_Trend_Following_Strategy.pdf`). Ingested 2026-06-18.
This is strategy **1 of 2** in the equities line ([../README.md](../README.md)).

## The strategy in one paragraph

A discretionary **swing momentum / trend-following** method built on one pattern (the
author calls it a *High Tight Flag*): a stock makes a **large prior thrust** (30%+, often
100–300%) on high volume → goes **sideways into the 10/20-day moving averages on
declining volume** forming a narrow-range base (3–20+ days, longer = better) → then
**breaks out** on volume higher than the prior day, closing at/near the high of day. Enter
the breakout, stop at low-of-day, **scale out 1/3–1/2 into strength after 3–5 days**, move
to breakeven, and **trail the rest with the 10/20 MA**. Trade only the **leading stocks in
leading sectors**, and **stand aside when the market regime is weak** (10MA < 20MA on SPY
or QQQ, or a 10%+ index correction).

## Author's claimed statistics (Monte Carlo, "perfect execution")

$10k start · 1000 trades · 100 sims, log scale:

| Metric | Value |
|---|---|
| Win probability | ~30% |
| Avg win:loss | 3:1 to 4:1 |
| Implied gross expectancy | ≈ +0.35R / trade (0.30·3.5 − 0.70·1) |
| Risk per trade | 1% (0.5% poor regime, 2% great, never >2%) |
| Avg max drawdown | 19.8% |
| Worst max drawdown | 35.4% |
| Max consecutive wins / losses | 9 / 35 |

These are the author's idealized claims — **our job is to test whether an honest,
mechanical version survives real fills, costs, walk-forward, and survivorship/universe
bias.** Expect realized to land below the claim.

## What this means for *us* (a backtesting lab)

The playbook is discretionary. To research it here we mechanize each rule into a
parameterized, no-lookahead, honestly-filled detector + backtest. The translation,
parameter defaults, controls, and the judgment calls that need registering live in
[SPEC.md](SPEC.md). Every test goes in [LEDGER.md](LEDGER.md).

## Data status

- **Have:** EOD + 1-min bars for 133 NDX-100 names, 2023-06 → 2026-06 (`../README.md`).
- **Gap 1 (regime filter):** SPY/QQQ not local → pull before the regime rule is testable.
- **Gap 2 (sector/leadership):** no sector ETFs / GICS map local → needed for the
  leadership + cycle models (SPEC §6.5).
- **Gap 3 (character screen):** float/shares-outstanding + earnings dates aren't in OHLCV
  (every doc example screens on them) → need a fundamentals + earnings-calendar source.
- **Caveat (universe):** the doc's own examples (HUT, UROY, AMR, SI) are low-float
  small/mid-caps and **none are in our NDX-100 data**; the strategy hunts 30–300% movers.
  A fair test wants a broader liquid-US-stock pull. NDX-100 = a conservative first pass.

## Status

- **Ingested + scaffolded 2026-06-18.** Text + all diagrams read ([DIAGRAMS.md](DIAGRAMS.md)).
  No code, no tests run yet.
- **Direction set (Ben):** model the discretion — strength/weakness, cycle/rotation, and
  setup-quality models replace the hand-coded proxies (SPEC §6.5).
- Awaiting: (a) strategy doc 2 of 2, (b) the §0 decisions (universe breadth, survivorship
  basis) before Phase 1.
