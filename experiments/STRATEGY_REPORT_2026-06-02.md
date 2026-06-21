# Strategy & Data Report — 2026-06-02

## Bottom line up front
You have **two validated edges** and a few promising directions. The constraint is **not ideas** — it's
**execution** (Mira) and **capital** (RV). The single highest-leverage thing in your whole operation is
getting Mira's auto-execution working. Everything else is mapped, validated, and waiting. The honest risk
right now isn't "no edge" — it's collecting more directions instead of shipping the one that's already live.

---

## The edges — what I think of each

### 1. Mira (MBO order-flow reclaim) — THE money-maker ⭐ | conviction: HIGH
- **What:** intraday reclaim on ES/NQ/RTY; entry on real order-by-order flow (MBO depth), tight stop, trail to ~2R.
- **Status:** CONFIRMED +0.44R OOS (Jan, n=139); stress-tested robust (all 4 symbols + both directions
  positive, survives 4 extra ticks slippage, intra-month drawdown only −7.5R); 3 live eval trades landing
  exactly where backtest trades land.
- **My take:** highest-conviction, highest-upside. It's the prop/milk engine, and it's *live*. The only open
  question is cross-month generalization (Jan is one month) — and the live eval is answering that for free.
- **Gated on:** EXECUTION (auto order placement via Rithmic — your other PC). **This is the bottleneck.**

### 2. RV book (diversified cointegration) — the "grow a real account" sleeve | conviction: HIGH (capital-gated)
- **What:** market-neutral spreads across energy + grains + rates curve + gold/silver (12 economically-linked pairs).
- **Status:** VALIDATED, OOS Sharpe **+1.44**, positive every year, half the drawdown of any single complex;
  100% positive across parameter settings.
- **My take:** genuinely robust, uncorrelated to Mira, high floor. But market-neutral = slow, and it's a poor
  fit for day-trading prop firms (multi-day holds).
- **Gated on:** CAPITAL — needs ~$75k+ for clean execution; you have none right now. Parked behind money.
- *(CL/BZ alone, OOS +1.54, is the simplest liquid starter when capital exists.)*

### 3. Options / gamma regime — the promising unknown | conviction: MEDIUM (worth the cheap test)
- **What:** use SPX/NDX options data (dealer gamma) to flag pin/mean-revert vs trend days → a **regime gate**
  for the index strategies. Could make Mira sharper, not replace it.
- **Status:** UNPROVEN — mapped (`options_signals_v0/RESEARCH_AGENDA.md`), not tested.
- **My take:** the most interesting *new* direction, and it fits (you trade the index). The durable part is the
  regime/vol effect, not direction-prediction (that's arbed/hyped). Data is shockingly cheap (~$75).
- **Gated on:** data (~$75) — but test the **free VIX proxy first**.

### 4. TSMOM (time-series trend) — parked | conviction: LOW right now
- Real but in a multi-year drought (OOS ~flat, dies on cost). The high-capacity / low-floor sleeve for when
  trends return. Not now.

### 5. Dead lanes — closed, don't re-chase
- Intraday price patterns (ICT / SMT / FVG / sweeps / reclaims *as chart patterns*) and index **direction
  forecasting** — all KILLED on clean data; the "edges" were data artifacts (wick noise, lookahead labels).
  The *only* survivor of that whole arc was Mira's **MBO order flow** — real microstructure, not patterns.

---

## The data — what to buy, what to skip

| data | cost | verdict |
|---|---|---|
| OHLCV-1m 15yr, all 28 syms | **$0** | **FREE — pull it.** Fills the lab's deep history for future ML. |
| VIX history (proxy test) | **$0** | **FREE — do first.** Gates the options spend. |
| **SPX+NDX options EOD bundle, 1yr** | **~$75** | **BEST-VALUE BUY.** Unlocks the whole gamma/regime direction for < 1 month of index MBO. After the free VIX proxy. |
| MBO energy 3mo | $28 | Defer — speculative (Mira-style flow on energy is unproven). |
| MBO index 1mo / 3mo / 9mo | $66 / $256 / $597 | **SKIP for now** — you wanted these to validate Mira more, but the **live eval is generating that forward evidence for free.** |
| MBP-1 all-28 1yr | $489 | Skip — you already have a year. |

---

## What I'd actually do (priority order)
1. **Get Mira executing** (other PC). The only thing between you and a first dollar. Nothing else matters as much.
2. **Free, now:** pull the $0 OHLCV history · run the VIX-proxy regime test · refine the bots · build the milk
   deployment playbook (which firms / how many accounts / what sizing) so it's ready the moment execution works.
3. **When you'll spend a little:** the **~$75 options bundle** (only if the free VIX proxy shows promise).
4. **Don't:** buy more MBO, re-chase dead lanes, or add a *fourth* direction before Mira is live and printing.

---

## UPDATE (same day) — free VIX proxy ran → options buy DOWNGRADED
Ran the free VIX-term-structure regime proxy before spending. It conditions realized vol (expected) but
**does NOT predict trend-vs-mean-revert** (corr +0.007, flat across regimes). So the gamma *regime gate*
— the actual reason to buy options data — got **no support from the cheap proxy.** Real GEX is sharper so
it's not a definitive kill, but **the ~$75 options buy drops from "best-value, go" to "speculative."**
Net effect: reinforces the priority order — execution first, options data is now a low-priority maybe.
Also done: kicked off the **$0 OHLCV 15yr deep-history pull** (running, filling 2011→2018 for 25 symbols).

**FINAL (same day) — bought the $75 SPX+NDX data, computed GEX, TESTED the gate → DEAD.** GEX conditions
realized vol (corr −0.16, redundant with VIX) but NOT trend-vs-mean-revert (corr −0.004, flat); the free
VIX proxy (+0.007) independently agrees. The daily gamma regime gate does not exist for ES. Killed for
$75 *before* any live build — cheap-first discipline worked. Also killed same day: **TGIF** (faithful
weekly test: noisy, inconsistent ES vs NQ, not tradeable) and generic **fractal expansion→reversion**
(beats baseline but ~breakeven; the one positive cell was index drift). **Options/gamma direction =
closed.** 3rd null on "predict ES intraday behavior." The real edges remain Mira (MBO) + RV (cointegration).

## The honest meta-point
You're generating validated edges **faster than you can execute them.** That's a good problem — but it means
your lever isn't more research, it's turning **one** edge into running income. Mira is that edge and it's ~90%
there. Get it executing → get the first payout → and the flywheel starts: payouts become capital, capital
deploys the RV book, a slice funds the $75 options test. **Everything compounds from execution.** Until Mira
fires its own orders, every new idea — including the good ones — is a distraction from the thing that's *this*
close.
