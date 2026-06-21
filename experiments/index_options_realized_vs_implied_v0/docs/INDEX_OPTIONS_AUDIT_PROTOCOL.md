# Index-Options Realized-vs-Implied Audit — v0 PROTOCOL — LOCKED 2026-06-14 (GPT-reviewed)

> **LOCKED by Ben 2026-06-14 after GPT review + all 5 fixes; run once, no post-result edits.**
> (history) scaffold built + GPT's 5 lock-fixes applied. Audit-first: build a
> state→payoff TABLE before any model. If the frozen primary bucket shows no economic separation after
> real option spread, we stop — no model, no intraday, no stocks, no MBO, no NDX. Same discipline that
> killed the stock-ranker. Fixes applied: (1) fail-closed settlement, (2) canonical vol-regime adapter,
> (3) frozen primary hypothesis VOLATILE×cheap, (4) same-DTE baseline within slice, (5) DTE +
> exclusion reporting.

## The question
> Given market state at close t, were SPX options **cheap or expensive** vs the next realized move,
> measured by a **quote-based** long-ATM-straddle payoff held to expiry, after bid/ask?

A description ("volatile/choppy") is not a trade. The trade exists only if a state bucket's
quote-based straddle P&L (buy at ask, settle to intrinsic) beats the same-DTE unconditional baseline.

## Data (verified 2026-06-14)
- Source: `bulk_hist_option_eod_greeks` (ThetaData cache, hash-keyed). SPX rows carry **bid, ask,
  underlying_price, implied_vol, greeks** per strike/expiry/date, **full 2018–2026**. Underlying is
  identified by strike band (reuse the walls-builder SPX classification); there is no root column.
- Realized: SPX `underlying_price` from the same chain (primary); ES 1m bars as a secondary proxy.
- Quotes use **bid/ask** — `close`/`volume` are 0 for untraded strikes, so close is unusable.

## LOCKED construction (primary)
For each entry date t (EOD chain at close t):
1. Select the **nearest eligible expiry** with **trading DTE in [1, 7]**.
2. **Settlement gate — FAIL-CLOSED (GPT fix #1).** The cache has no settlement/root field, so we
   cannot positively confirm PM settlement. EXCLUDE the whole monthly-expiry risk zone:
   **day-of-month 15–21 AND weekday Thursday/Friday** (catches the 3rd-Friday AM/SET monthly and any
   holiday-shifted-to-Thursday monthly). This drops some valid PM weeklies/dailies — accepted, vs
   silently settling an AM contract at the close. **Log** `am_risk_expiries_excluded_count/dates` and
   `included_expiry_count` by year and DTE; if exclusion is too costly, source real settlement metadata
   before running. (`S_expiry` = EOD `underlying_price` is a PM-settle **proxy**, fine for Mode A; if a
   bucket is borderline, re-verify with true settlement before calling PULSE.)
3. **ATM strike:** K minimizing |K − underlying_price|; both call & put at K must have valid quotes
   (`ask ≥ bid > 0`, `mid > 0`). Search the nearest 3 strikes by distance; take the first valid
   call+put pair; log if not the exact nearest. **Never** pick the most-liquid/profitable strike.
4. **Quote filters (frozen):** `bid>0`, `ask>bid`, `mid>0`, same strike & expiry for call/put,
   `underlying>0`, DTE∈[1,7], settlement valid, and `straddle_spread/straddle_mid ≤ 0.20`
   (`straddle_spread = (call_ask−call_bid)+(put_ask−put_bid)`). Report sensitivity at 0.10 / 0.20 /
   none; **primary threshold = 0.20 frozen.**
5. **Enter long straddle at ask**, **hold to expiry, settle to intrinsic.**

### Primary P&L (points; also report % and R)
```
entry_cost_ask   = call_ask + put_ask
settlement_value = max(S_exp - K, 0) + max(K - S_exp, 0) = |S_exp - K|
pnl_points       = settlement_value - entry_cost_ask - fees
pnl_pct          = pnl_points / S_t          # primary economic unit
pnl_R            = pnl_points / entry_cost_ask   # secondary; explodes for cheap options
```

### Implied move
```
tradable_implied_move_pct = (call_ask + put_ask) / underlying_price   # primary (what you pay)
mid_implied_move_pct      = (call_mid + put_mid) / underlying_price   # diagnostic
atm_iv * sqrt(dte/252)                                                # diagnostic only
```

## State buckets (9) and the FROZEN primary hypothesis
`vol_regime × implied_move_rank`
- **vol_regime** ∈ {CALM, NORMAL, VOLATILE} from the **canonical validated** vol-regime
  (`validation/vol_regime_adapter.py`, which replicates `market_state/state_monitor.py`'s exact
  methodology — MAD vol, 20-win, 504 rank, 33/66 cuts — per-date and no-lookahead, on ES.c.0). GPT
  fix #2: the local `realized_vol_percentile_regime` is an **unvalidated fallback only**, never the
  primary.
- **implied_move_rank** ∈ {cheap, mid, rich} = rolling **prior-252-observation** percentile of
  `dte_norm_implied_move = (straddle_mid/underlying) / sqrt(trading_dte)`; cheap=bottom 33%,
  rich=top 33%. Uses ONLY observations strictly before t (no-lookahead test enforces this).
- **Quote-derived** straddle-implied-move rank is primary; vendor ATM-IV rank is a secondary
  diagnostic (if IV says cheap but the ask is expensive, the trade loses — rank the tradable thing).

### FROZEN primary hypothesis (GPT fix #3 — anti bucket-shopping)
**Only `VOLATILE × cheap` is eligible for PULSE/EDGE.** Long-vol thesis: cheap-priced straddles in a
volatile regime should under-price the realized move. The other 8 buckets are **diagnostics** and can
**never** be promoted to a pass after the run. "Look at 9 buckets, call the best one a pulse" = the
stock-ranker trap in options form. `classify_primary()` evaluates only this bucket.

Secondary/exploratory (NOT promotable in v0): the other 8 buckets, ATM-IV rank, term structure, skew,
day-of-week, month, event flags, ES-realized proxy, NDX/NQ. **No MBO, no stocks, no gamma, no intraday.**

## Baseline, significance, pass/fail
- **Baseline: same-DTE unconditional long straddle, computed WITHIN the reported slice** (GPT fix #4
  — not full-sample if the table is an evaluation report; a rich/cheap bucket must beat its DTE-matched
  peers *in the same period*, else it's a DTE-composition artifact). Report per bucket: raw P&L,
  same-DTE baseline P&L, **bucket edge = bucket − same-DTE baseline**, and the **DTE distribution**
  (min/median/max). Also report the settlement-exclusion counts (GPT fix #5).
- **Significance:** HAC/Newey-West SE with **lag = 7** (max DTE → overlapping windows); report MDE.
  Robustness: year-by-year table, drop-best-5-expiries, drop-best-5-days, 1.5× spread stress.
- Pass/fail is evaluated **only on the frozen `VOLATILE × cheap` bucket** (`classify_primary`):
- **PULSE:** n ≥ 100; quote-based P&L (ask-entry, intrinsic settle) > 0; **bucket edge over same-DTE
  baseline > 0**; HAC t > 1.5 or |edge| > MDE_95; survives 1.5× spread stress (near breakeven or
  better); not driven by 2020 / one year / best-5-expiries.
- **EDGE:** HAC t > 2; positive after 1.5× spread stress; beats same-DTE baseline; positive across
  multiple chronological blocks; drop-best-5-expiries stays positive.
- If only **secondary** buckets look positive → **diagnostic hint only, no model.**
- **NO PASS → no model.** If only mid-to-mid / realized-implied-ratio / before-spread / one crisis
  year is positive, stop.

## Two modes (label honestly)
- **Mode A (pricing audit):** quotes at close t, settle at expiry. "Was SPX under/overpricing the move?"
- **Mode B (execution stress):** state known at close t, enter at next tradable quote. Later diagnostic.
v0 is Mode A; do not call it live-tradable.

## Cost tiers
Tier 0 mid-to-mid (diagnostic) · **Tier 1 ask-entry + intrinsic settle (PRIMARY)** · Tier 2 1.5× spread
stress · Tier 3 reject dirty/wide quotes.

## Deliverables (this scaffold) — no run yet
options/{chain_loader,expiry_selection,implied_move,straddle_proxy}.py ·
validation/{state_buckets,vol_regime_adapter,significance,index_options_payoff_audit}.py ·
tests/{test_no_lookahead_implied_move_rank,test_straddle_bid_ask_math,test_expiry_selection_dte_band,
test_settlement_filter}.py · reports/. Lock → run once → report vs the ladder is the next gate.
