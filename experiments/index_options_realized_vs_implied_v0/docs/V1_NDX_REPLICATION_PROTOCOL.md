# v1 — NDX Independent-Product Replication — LOCKED 2026-06-14 (GPT-reviewed)

> **LOCKED by Ben 2026-06-14; run once, no post-result edits.** ONE replication test, then stop.
> Inherits v0's machinery (fail-closed settlement, prior-252 rank, DTE[1,7], 0.20 spread filter, HAC
> lag 7) except as noted. STOP rule: fail/unresolved → shelve the index-options line (no RUT/DJX/SPX recuts).

## The one hypothesis (frozen)
> **NDX straddles with a rich quote-derived implied-move rank are overpriced relative to the realized
> move. Therefore shorting RICH ATM straddles should outperform (a) same-DTE unconditional short
> straddles and (b) shorting CHEAP ATM straddles, after bid/ask costs and tail accounting.**

This is an **independent-product replication** of the SPX v0 diagnostic — NOT a new bucket search, NOT
a short-vol strategy hunt. The SPX 9-bucket diagnostic (incl. the accidental NORMAL×cheap t=2.12) is
**not** promoted; v1 tests only the broader economic structure `RICH-short > CHEAP-short`.

## Why NDX
SPX 2020–26 ~1-DTE is **peeked**. A different SPX DTE cut = "try slices until one prints." NDX is a
genuinely different underlying / option market / liquidity profile, full 2018–26 raw prices with real
bid/ask on disk (no vendor greeks needed — we use quotes, not IV). It's an honest replication, not a
clean-room confirmation. **Order: NDX once → if pass, defined-risk iron-fly / forward log → if fail, SHELVE.**

## Frozen construction
- **Product: NDX only.** Underlying = NQ.c.0 daily close (NDX≈NQ, ratio ~1.0, validated). Realized /
  settlement S_exp = NQ close at expiry (PM-settle proxy, Mode A).
- **Instrument: naked short ATM straddle — AUDIT MEASURING INSTRUMENT ONLY.** Sell at bid, hold to
  expiry, settle to intrinsic. **No live naked short. No deploy claim.** Deployable expression (iron
  fly) is a *later* protocol, only if v1 passes.
- **Expiry/settlement:** v0's fail-closed rule — nearest PM-settled expiry, trading DTE∈[1,7], exclude
  the monthly-risk zone (day 15–21 AND Thu/Fri); if NDX settlement is ambiguous, **fail closed**.
- **Expensiveness rank (NDX's OWN, not SPX thresholds):** `implied_move_rank` = rolling prior-252
  percentile of `(straddle_mid/underlying)/sqrt(trading_dte)`; CHEAP ≤ 33rd, MID, RICH ≥ 66th.
- **Quote filters (frozen):** bid>0, ask>bid, mid>0, `straddle_spread/straddle_mid ≤ 0.20`, DTE∈[1,7],
  same strike call/put, nearest valid ATM pair. Diagnostics at 0.10 / 0.20 / none — never loosen primary.

### Short P&L + costs
```
entry_credit  = call_bid + put_bid
settle_loss   = |S_exp - K|
short_pnl     = entry_credit - settle_loss - fees
units:  pnl_points · pnl_pct_underlying (PRIMARY) · pnl_R = pnl / entry_credit
1.5x spread stress:  stress_credit = entry_credit - 0.5 * straddle_spread
                     (straddle_spread = (call_ask-call_bid)+(put_ask-put_bid))
```

## Baselines (3) and the separation test
1. same-DTE unconditional short straddle  2. short CHEAP  3. short ALL eligible.
Primary comparisons (within the reported slice): **`short_RICH − same-DTE unconditional`** and
**`short_RICH − short_CHEAP`**. Also report monotonicity `RICH ≥ MID ≥ CHEAP` for short P&L. (If
RICH-short and CHEAP-short work equally, it's generic VRP, not a state edge — that's a fail of the
*separation* test.)

## Tail accounting (mandatory — it's a risk premium, not alpha)
Report by bucket: `CVaR5_pct_underlying`, `CVaR5_R`, `worst_loss_R`, `P(pnl_R < -3)`, `P(pnl_R < -5)`,
and `mean_pnl_pct / |CVaR5_pnl_pct|`.

## Pass/fail (evaluated only on RICH-short)
**PULSE:** n_rich ≥ 250; mean short-RICH pnl_pct > 0; beats same-DTE unconditional short; short-RICH −
short-CHEAP > 0; HAC t on short-RICH excess > 1.5 OR excess > MDE_95; 1.5× spread-stress positive or
flat; `mean_pnl_pct/|CVaR5_pnl_pct| ≥ 0.03`; `P(R<−3) ≤ 5%`; `P(R<−5) ≤ 2%`; not one-year /
crash-cluster driven.
**EDGE:** HAC t > 2; positive after 1.5× stress; beats same-DTE baseline and CHEAP-short;
`mean/|CVaR5| ≥ 0.07`; `P(R<−3) ≤ 3%`; `P(R<−5) ≤ 1%`; drop-worst-5-expiries tail still acceptable;
positive across multiple subperiods.
**If mean is positive but the tail ratio fails → "VRP exists, naked expression not harvestable"** →
next step only if a defined-risk iron fly could plausibly reshape the tail.

## Robustness (report all)
HAC lag 7; MDE; year-by-year; 2018–19 / 2020–22 / 2023–26 subperiods; drop-worst-5-expiries;
drop-best-5-expiries; drop-2020; drop-2022; DTE distribution by bucket; quote-spread distribution by
bucket; tail metrics by bucket. No fitted parameters (replication) → full post-warmup NDX sample.

## STOP rule (frozen)
**If NDX v1 fails or is unresolved → the index-options realized-vs-implied line is SHELVED. No
RUT/DJX/SPX-DTE recuts.** If it passes → defined-risk iron-fly protocol or forward paper log; **no live
naked short, no deploy.**

## Deliverables (this draft) — no run
options/chain_loader.py:build_ndx_chain · straddle_proxy.py:short_straddle_pnl(_stressed) ·
validation/tail_metrics.py · validation/run_v1_ndx.py (main raises until locked) ·
tests/{test_short_straddle_math,test_tail_metrics}.py
