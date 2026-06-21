# index_options_realized_vs_implied_v0

**Audit-first** research: were SPX options cheap or expensive vs the next realized move, by market
state? Build the state→payoff TABLE before any model. If no `vol_regime × implied_move_rank` bucket
beats its same-DTE baseline after real bid/ask, we stop — no model, no intraday, no stocks, no MBO,
no NDX. (Born after the daily single-stock ranker — `index-stock-vol-alpha` — was shelved on two
clean pre-registered negatives; this routes options through BacktestStation's strong index-options
+ vol-regime assets instead.)

Spec is locked-pending-final-review in [`docs/INDEX_OPTIONS_AUDIT_PROTOCOL.md`](docs/INDEX_OPTIONS_AUDIT_PROTOCOL.md).

## Layout
```
options/chain_loader.py       SPX EOD greeks chain (bid/ask/underlying/IV) from the ThetaData cache
options/expiry_selection.py   nearest PM-settled expiry, trading DTE in [1,7] (3rd-Friday AM excluded)
options/implied_move.py       ATM strike pick, straddle quotes, implied move, quote filters
options/straddle_proxy.py     buy-at-ask, hold-to-expiry, settle-intrinsic P&L (+1.5x spread stress)
validation/state_buckets.py   vol_regime × implied_move_rank (prior-252 percentile, no-lookahead)
validation/significance.py    Newey-West HAC (lag 7) + MDE
validation/index_options_payoff_audit.py   orchestrator: entries → bucket table (NOT run yet)
tests/                        no-lookahead rank, straddle bid/ask math, DTE band, settlement filter
```

## Status — SHELVED 2026-06-14 (ran once, NO PASS, did not replicate)
v0 SPX LOCKED run: frozen primary `VOLATILE × cheap` = **NO PASS** (n=53, edge +0.0004, HAC t +0.44 vs
1.5 needed). The variance risk premium dominates — straddles over-price the move (median realized/implied
0.84). The only HAC t>2 bucket (NORMAL × cheap, t=2.12) is NOT the frozen primary → promoting it would be
bucket-shopping. v1 NDX independent-product replication of that cheap-vs-rich diagnostic: **NO PASS and it
INVERTED** (rich−cheap −0.00028, monotonicity false) → it was SPX-window / multiple-comparisons noise, and
the naked short tail is un-harvestable regardless. **Per the locked STOP RULE → the index-options
realized-vs-implied line is SHELVED** (no RUT/DJX/SPX recuts). See `docs/RESEARCH_LOG.md` and
`reports/{index_options_audit,v1_ndx_replication}_2026-06-14.txt`. The harness + discipline are the durable
assets; the edge was not there. (Run 2026-06-14, not yet committed.)
