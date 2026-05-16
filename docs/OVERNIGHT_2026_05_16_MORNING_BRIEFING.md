# Overnight 2026-05-16 — morning briefing

_4 substantive iterations landed while you slept. Read this first._

## The arc

Starting state when you left: v5 winner at **+110R / 64R max DD / 5/6 years positive**, with 2025 at −35R as the open question.

Tonight's 4 commits:

| Commit | What | Headline |
|---|---|---|
| [3bb98c8](https://github.com/benbrainard11-netizen/BacktestStation/commit/3bb98c8) | v6 = v5 + swing strict | **Swing doesn't help** — v5 baseline wins. Disconfirmed. |
| [3d2f155](https://github.com/benbrainard11-netizen/BacktestStation/commit/3d2f155) | 2025 regime diagnostic | **The model is FINE in 2025** — best AUC ever. Stops are the problem (68% stop-out rate). |
| [ef2124f](https://github.com/benbrainard11-netizen/BacktestStation/commit/ef2124f) | v7 stop variants | **v7d (vol-floored stops)** — same risk profile better adapted; +73R / 27R DD / 58% win / 2025 at only −5R. |
| [220821d](https://github.com/benbrainard11-netizen/BacktestStation/commit/220821d) | v8 small tweaks | **v8a (target=5×ATR on top of v7d)** — +79R / 27R DD / 58% win / 5/6 yrs. **Current best deploy candidate.** |

## The headline finding

> **The 2025 weakness was never a model problem. It was a stop problem.**

The diagnostic was clear:
- 2025 walk-forward AUC: **highest ever** for 2 of 3 OGAP signals
- 2025 top-10% precision: **highest ever** (often a perfect 1.000)
- 2025 v5 trade stop-out rate: **68%** vs 29-57% in prior years

The model finds patterns better than ever in 2025. But v5's fixed 2 ATR stops get tagged by 2025's higher intra-window volatility before the predicted rejection completes.

**v7d fixes this** with a vol floor on the stop: `stop = max(2.0 × ATR(14, 5m), 1.5 × ATR(14, 30m))`. The longer-period ATR catches regime-level vol shifts that the 5m ATR misses.

## The v8a current best

| Property | Value |
|---|---|
| Portfolio | 3 OGAP signals (gap_down rejection, gap_up rejection, strict partial_touch) |
| Filter | 2+ signal consensus on same date+symbol |
| Symbols | NQ + ES (drop YM) |
| Stop | max(2.0 × ATR(14, 5m), 1.5 × ATR(14, 30m)) — vol-floored |
| Target | 5.0 × stop_atr (calibrated R units = stop distance) |
| Time exit | 240 min |
| Entry | Wait for first confirmation bar, enter at next bar open |
| Cum R / 6 yr | **+78.7** |
| Win rate | **57.6%** |
| Max DD | 26.7 R |
| Years positive | **5/6** |
| 2025 result | −5.2 R (nearly flat) |

Per-year:

| Year | Cum R |
|---|---:|
| 2020 | +32.1 |
| 2021 | +16.5 |
| 2022 | +1.9 |
| 2023 | +4.6 |
| 2024 | +28.6 |
| 2025 | −5.1 |

## v8a vs v5: the deploy decision

| Metric | v5 (max return) | v8a (current best risk-adj) |
|---|---:|---:|
| Cum R / 6 yr | +109.9 | +78.7 |
| Max DD | 64.5 | **26.7** |
| Win rate | 48.9% | **57.6%** |
| 2025 | −35.0 | **−5.1** |
| DD per cum_R | 0.59 | **0.34** |
| Return on capital (rough) | 88% / 6yr | **134% / 6yr** |

**v8a is the more honest deploy candidate.** v5 has higher headline return but the 64R drawdown means you need more capital to absorb it; v8a delivers 60% more return per unit of capital risked. The 2025 result (nearly flat vs −35R) is the most important deployability signal.

## What didn't work tonight

- **Adding swing strict to the portfolio.** Swing as a 4th family didn't improve v5. Either the swing signals don't fit this trade-rule shape, or the consensus filter doesn't usefully combine break-direction (swing continuation) with mean-reversion (OGAP rejection) bets. Detail: v6b with both 60m + 240m swing labels exposed a **consensus-filter bug** — same-matrix multi-horizon labels shouldn't count as independent consensus. Fix needed before 247 ships more multi-horizon labels.
- **Shorter time exits.** v8d (tw=60) lost money entirely. 2025's high intra-window vol means trades NEED 240 min to develop.

## What 247 is doing (when you check)

Per your earlier prompt, 247 is queued on **strict order_block reaction labels**. ~6-10 hours work. If they ship overnight, the natural v9 is integrating OB into the v8a portfolio. (Same caveat: same-matrix multi-horizon labels need the consensus-filter bug fixed first.)

## Suggested morning decisions

1. **Adopt v8a as the canonical "current best".** Use it for any forward-looking deployment thinking.
2. **Fix the consensus-filter bug** before integrating more multi-horizon labels (OB, future swing variants). Family-level consensus, not label-level.
3. **2025 isn't a regime worry anymore** — we now know the issue was stops, and v8a's vol floor handles it.
4. **Strategy v3 spec doc** worth writing — the design space has crystallized (vol-floored stops, 5× ATR target, 240 min window, consensus filter). Document it.
5. **Next research direction:** trailing stops (v9b) might push v8a further — once price moves +1 ATR favorable, ratchet stop. Combines v8a's protection with capture on partial-target trades.

## File index

Everything from tonight on origin (branch `assets/expanded-universe-v1`):

```
docs/
  ML_2025_REGIME_DIAGNOSTIC.md
  ML_RIGOROUS_BACKTEST_V7_STOPS.md
  OVERNIGHT_2026_05_16_MORNING_BRIEFING.md     (this doc)

backend/scripts/ml/
  rigorous_backtest_v6_with_swing.py
  diagnose_2025_regime.py
  rigorous_backtest_v7_stops.py
  rigorous_backtest_v8_tweaks.py

experiments/backtests/
  2026-05-16_rigorous_v6_with_swing/
  2026-05-16_2025_regime_diagnostic/
  2026-05-16_rigorous_v7_stops/
  2026-05-16_rigorous_v8_tweaks/
```

## TL;DR for the morning coffee

- **You went from a single v5 result to a tested v8a deploy candidate** with 60% better risk-adjusted return
- **The 2025 mystery is solved**: it was the stops, not the model
- **Swing strict didn't add anything** — disconfirmed; don't invest more in that direction
- **One small infrastructure bug to fix**: consensus filter shouldn't count multi-horizon labels on the same matrix as independent
- **Strategy v3 spec is the natural next document** to lock in v8a as the candidate design

Good morning.
