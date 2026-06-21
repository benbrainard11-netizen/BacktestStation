# DIAGRAMS — what the source-doc images show

The source PDF is mostly annotated chart screenshots (text extraction missed them). These
are our descriptions of the instructive ones; raw images sit in
`C:\Users\benbr\Downloads\momentum_imgs\` (third-party, not committed). Captured 2026-06-18.

## Setup examples (the 5-star pattern in the wild)

All from TC2000, MAs shown: **MA10 (purple), MA20 (blue), MA50 (black), EMA200 (red)**.
Every header carries **ADR%, ATR, Float, Market Cap, Earnings date** — these are screen
inputs, not decoration.

| Img | Name | Sector | Float | ADR% | Annotated points |
|---|---|---|---|---|---|
| p03 | HUT (Hut 8 Mining) | Crypto/Financial | 174M | 8.9 | "big uptrend, surfs MAs" → "price tightens on MA" → "breakout day" + "increased volume" |
| p04 | TSLA | Auto / Consumer Cyclical | — | 4.0 | "big uptrend hot sector"; symmetrical-triangle base; "breakout day" + volume |
| p05 | UROY (Uranium Royalty) | Uranium / Basic Materials | 95.5M | 7.6 | two breakouts (initial + re-break after a flag), volume on both |
| p06 | LCID (Lucid) | Auto / Consumer Cyclical | 572M | 6.1 | two breakout points up the MA10, increased volume |
| p07 | SI (Silvergate) | Regional Bank / Financial | 31.4M | 6.5 | two breakouts out of a long base, two volume surges |

Takeaway: **low-float, mid-ADR small/mid-caps across rotating sectors** — *none of
HUT/UROY/AMR/SI are NDX-100*, confirming the universe-breadth gap (SPEC §0.2).

## Trade lifecycle (the exact management rules)

- **p09 AMR (coal):** one chart, three labels — **"Enter on breakout day risking 1%, stop
  LOD"** → **"Sell 25–50% into momentum and move stop to breakeven"** → **"Sell last of
  position on close of 10-day MA."** This pins the management: partial 25–50%, BE, then
  exit the runner on the **first daily close below MA10**.
- **p08 HUT trade:** **"Enter on initial gap up but stopped out. Since this is still a
  valid setup the next day can provide another entry… test the waters multiple times until
  you nail the setup."** → **re-entry after a stop-out is an explicit rule.** Also:
  "trailing with the 10-day MA; we stay in as long as daily close ≥ MA10; the arrow marks
  the first close below MA10 = exit." (One trade = +80% over ~1.3 months in their example.)

## Regime filter (p14, QQQ, COVID 2020)

- **"10MA crosses below the 20MA → bear market starts"** (stop taking breakouts).
- **"10MA crosses above 20MA → breakouts can be traded again."**
- Mechanical: gate new entries on the sign of (MA10 − MA20) of SPY/QQQ.

## Sector rotation cycle (p15) — the conceptual model

Classic economy-vs-market phase diagram (two phase-shifted sine waves, Economy blue /
Market red). Cycle and the sectors that lead each phase:

| Phase | Leading sectors |
|---|---|
| Market Bottom / Full Recession | Finance, Technology, Cyclicals |
| Early Recovery → Bull Market | Technology, Industrials, Basic Materials |
| Market Top | Basic Materials, Energy, Staples |
| Bear Market / Full Recovery | Energy, Staples, Healthcare |
| Early Recession / Late Bear | Healthcare, Utilities, Finance |

This is the target for the **cycle/rotation model** (SPEC §6.5): infer cycle phase from
data and rank which sectors are receiving rotation, instead of hand-labeling phases.

## Monte Carlo equity curve (p01)

100 sims × 1000 trades, log y-axis ("Alpha"), all paths slope up from ~$7,860 into a fan
from ~$360k to ~$4.5M — the visual behind the claimed-stats table (README). Idealized,
perfect-execution; our job is the honest version.
