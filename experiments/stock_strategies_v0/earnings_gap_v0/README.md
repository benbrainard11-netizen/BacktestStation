# earnings_gap_v0 — earnings gap-up continuation swing strategy

Source: *Earnings Strategy* (discord.gg/sartrading mentorship PDF,
`C:\Users\benbr\Downloads\Earnings_Strategy.pdf`). Ingested 2026-06-18.
Strategy **2 of 2** in the equities line ([../README.md](../README.md)).

## The strategy in one paragraph

Trade the **fundamental catalyst**: a stock that has gone **sideways for a long time**
(weeks–months) and then prints an **unexpected earnings beat** gaps up hard and tends to
**drive higher for weeks to months**. Buy the good gaps, avoid the bad ones. Entry on the
gap-up earnings day (same 1-min trigger as the trend strategy), stop = low of day, **scale
1/2 into strength at day +3–5 → breakeven**, trail the runner with the 10/20 MA, exit on a
candle **close below the 10/20 MA**. Low frequency; the author says to **run it alongside
the trend strategy** ([../momentum_trend_v0](../momentum_trend_v0/README.md)) and notes it
**works best in stronger market cycles**.

## Setup criteria (the gap filter)

1. **Gap up > 7.5%** on the open.
2. **Earnings day**, gap appears **in premarket**.
3. **Open > previous day's high.**
4. **Above-average volume** in premarket **and** the first 30 min of the open.
5. Enough **liquidity** for the account size.
- Plus (text + p02 diagram): a **long sideways base** before the gap, and the gap must clear
  resistance — **gap *above* resistance, not *into* it** — on **high volume**.

## Author's claimed statistics (Monte Carlo, "perfect execution")

$1,000 start · 1000 trades · 100 sims, log scale:

| Metric | Value |
|---|---|
| Win probability | ~40% |
| Avg win:loss | ~3:1 |
| Implied gross expectancy | ≈ +0.60R / trade (0.40·3 − 0.60·1) |
| Avg / worst max drawdown | 13.7% / 22.4% |
| Max consecutive wins / losses | 11 / 21 |

Better-behaved than the trend strategy on paper (higher win rate, shallower DD), but
**lower setup frequency** — hence "combine with the trend strategy." Our job is the honest,
mechanical version after fills/costs/walk-forward.

## Relationship to the trend strategy (shared shell)

The two strategies share the **entire execution shell** — 1-min entry trigger, stop = LOD,
1/2 partial → BE at day +3–5, trail/exit on close below MA10/20, 1%/2% sizing with 30% max
exposure, honest fills. They differ only in the **setup detector** (technical flag breakout
vs. earnings gap-up). So: **one shared execution + sizing + fill engine, two detectors** —
captured at the umbrella level. The earnings "stay out of the bad gaps" judgment is the
ML target here (see SPEC §6).

## Data status

- **Have:** EOD + 1-min RTH bars for 133 NDX-100 names, 2023-06 → 2026-06 (`../README.md`).
- **Gap A (earnings calendar):** no earnings dates local → `yfinance` (installed) gives
  historical earnings dates for free; or a paid/ThetaData source. Required to even define
  the setup.
- **Gap B (premarket):** our 1-min bars are **RTH-only (09:30–15:59 ET)** → "premarket gap
  / premarket volume" criteria need an extended-hours re-pull. The gap itself (open vs.
  prior close/high) and first-30-min RTH volume are computable now.
- **Caveat (universe):** earnings gaps hit large caps too, so NDX-100 is less of a mismatch
  here than for the trend strategy — but a broader universe still gives more setups.

## Status — VALIDATED EDGE (2026-06-18)

Built + validated end-to-end (full detail in [LEDGER.md](LEDGER.md)):
study → out-of-sample edge → broad generality (1,495 names) → honest concurrency-aware
portfolio → regime test → selection model → intraday fill realism. **Verdict: a genuine,
modest, real edge** — ~16% CAGR / ~31% DD / Calmar ~0.5 OOS with the selection model; a
decent *component*, not a standalone money machine. Monte Carlo (validated strategy): median
~17% CAGR, 97% profit over 5y, but 23% avg / 38% worst drawdown. Pipeline: run_earnings_study
→ validate_earnings → run_portfolio → run_regime → build_features/run_model → run_intraday_check
→ run_montecarlo_final.

## Future avenues (not built; logged for when this is revisited)

**Harden → deploy decision:**
- **Survivorship fix** — point-in-time / delisted names (Norgate/Sharadar). Biggest honesty
  gap; the true CAGR/Calmar is likely below the survivorship-biased figure.
- **Sealed-holdout read** (2025-10 → now) — the one-shot final verdict; spend only at the
  deploy decision (2 lifetime reads).
- **Full intraday execution** at scale (premarket m1_eth across names) — currently fill
  realism only checked on 133 NDX names.

**Extend the edge:**
- **Short side** — do earnings gap-DOWNs drift down (symmetric PEAD)? Untested; could add
  ~uncorrelated trades.
- **Surprise-driven PEAD** — the academic version keys on EPS surprise (SUE), not just the
  gap. We have surprise (~33% coverage); a surprise-conditioned version may be cleaner.
- **Big-gap sub-strategy** — drift is strongest in >15% gaps (+5.4%/20d); a focused variant.
- **Better selection model** — current OOS IC is weak (+0.045); add sector, analyst
  revisions, richer surprise/context features.

**Options expression (hybrid options/shares) — decision rule (logged 2026-06-18):**
- **Options (deep-ITM calls)** for: liquid-option names that are EXPENSIVE and/or have WIDE
  stops → capital efficiency (frees capital → take more of the ~64% currently-skipped
  signals) + defined risk (premium caps gap-through loss). IV crush is NOT a problem — entry
  is POST-earnings (post-crush). Theta is the drag → deep-ITM, not OTM.
- **Shares** for: everything else (illiquid options = most mid/small caps; tight-stop /
  cheap names).
- A later optimization, mainly valuable if capital-constrained. Backtesting the options
  sliver needs per-name historical option chains (a real data build).
