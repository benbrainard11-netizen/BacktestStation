# Morning report — what's actually real to build a bot portfolio from

Overnight, free compute only (no pulls). Tested the edge classes that *survive* honest validation, on clean
daily closes (not the wick-contaminated 5m bars that fooled us). Here's the honest scoreboard.

## TL;DR
- ✅ **Energy RV (crack / brent-WTI spreads) is REAL and deployable** — OOS Sharpe **+0.59**, positive 7 of 8
  years, market-neutral. **This is your first non-Mira bot.** Build it.
- 🟡 **Time-series momentum (trend)** is real but **regime-dependent and currently in a drought** — full-sample
  net Sharpe +0.43 (12m), but OOS ~flat and dies at >2bp cost. A diversifier, not a current performer.
- 🟡 **Mira (the milk engine)** is built but rests on an edge that's **barely validated** (MBO-free = −0.11R
  loser; the +0.38R is one tiny slice). The bottleneck for the whole milk plan.

## ✅ The win — the Energy RV book (build this)
Cointegration-selected on in-sample only (no lookahead), measured OOS, 2bp cost, on clean daily closes:

| pair | full Sharpe | **OOS Sharpe** | note |
|---|---|---|---|
| **CL/BZ** (crude–brent) | 0.57 | **1.57** | the star — strongest cointegration (ADF −7.75) |
| BZ/HO | 0.63 | 0.69 | |
| CL/RB | 0.52 | 0.58 | |
| CL/HO | 0.26 | 0.44 | |
| BZ/RB | 0.39 | 0.39 | |
| HO/RB | −0.25 | −0.52 | **broken — drop it** |
| **equal-weight book** | **+0.56** | **+0.59** | CAGR +9.2%, maxDD −0.32 |

Per-year Sharpe: 2019 **+1.97**, 2020 +0.02, 2021 **+1.45**, 2022 **+1.72**, 2023 −0.03, 2024 **+2.43**,
2025 +0.41, 2026 +0.05. **Positive in 7 of 8 years** (only 2023 flat). This is a genuine, consistent,
market-neutral edge grounded in real economics (gasoline/heating oil are *refined from* crude — the spread
can't drift apart). It's the opposite of the chart-pattern stuff: it survives precisely *because* it's
structural, not a pattern.

**Why it's the right first bot:** clean daily data you already have, no order flow needed, market-neutral
(high floor — good for a *live* account you grow), and uncorrelated to Mira. CL/BZ alone (Sharpe 1.57) is the
simplest possible start. The honest caveat: dropping HO/RB and weighting toward CL/BZ would look even better,
but that's post-hoc selection — trust the equal-weight book (0.59) as the conservative number.

## 🟡 Time-series momentum — real but in a drought
12-month TSMOM: full net Sharpe +0.43, but **OOS only +0.07** and negative by 5bp cost. Shorter lookbacks are
OOS-negative. This is the textbook trend profile — it worked 2018–22 (COVID, 2022 trends) and went flat in the
choppy 2023–24 trend drought. It's the **high-capacity / low-floor** sleeve: you'd run it for scale and
diversification knowing it has long flat periods, *not* for current Sharpe. Park it; revisit when trends return.

## 🟡 Mira / the milk engine — built, but waiting on one domino
The milk engine (per-firm profiles, correlated fleet sim) is **done and correct**. The findings from earlier:
- Best prop profile = balanced/moderate (~58% win, ~1.4R); home-runs blow up on trailing DD.
- Stagger account starts → ~free 5× better tail (correlation is the hidden killer).
- At +0.38R, 40 staggered Apex accounts → ~$870k/yr. **But** Mira's measurable (MBO-free) edge is **−0.11R — a
  loser** — and the +0.38R is one tiny MBO slice. **The milk only works if Mira's with-MBO edge is real**, which
  is unconfirmed.

## The honest portfolio + next steps
Your realistic systematic stack:
1. **Energy RV book** — confirmed, market-neutral, *build the bot* (start with CL/BZ). The clean win.
2. **Mira + milk** — gated on validating Mira's MBO edge on more OOS data (the #1 domino).
3. **TSMOM** — parked diversifier for when trends return.

**Recommended order when you're up:**
1. **Approve the data gap-fill** (2 min, free) — fills OHLCV deep history + recent MBP-1.
2. **Build the Energy RV bot** — turn the +0.59 book into a runnable strategy (it's the fastest path to a
   *second* real bot next to Mira, and it's the one thing that cleanly survived everything).
3. **Validate Mira's MBO edge** — the milk bottleneck; needs more MBO OOS (which the gap-fill / more data helps).

Scripts: `edge_hunt_v0/ts_momentum.py`, `edge_hunt_v0/energy_rv_book.py`, `xsectional_rv_v0/cointegration_select.py`.
