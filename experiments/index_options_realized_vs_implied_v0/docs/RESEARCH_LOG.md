# Research log

## 2026-06-14 — v1 NDX REPLICATION: NO PASS (did not replicate; inverted) -> index-options line SHELVED

Ran the locked NDX independent-product replication ONCE (protocol_sha 34b44f9c). Built NQ@16:00-ET as the
NDX underlying proxy (NDX raw-price files lack underlying_price; NDX~=NQ ratio 1.0); near-ATM NDX EOD chain
2018-2026 (3.16M rows). 1684 short-straddle entries (2019-05..2026-06), DTE mostly 1-2 (NDX has no dailies
like SPX -> genuinely different DTE mix).

FROZEN HYPOTHESIS (short RICH > short CHEAP and > same-DTE unconditional): NO PASS, and it INVERTS.
  cheap short mean +0.00007 | mid +0.00005 | RICH -0.00021  -> monotonicity RICH>=MID>=CHEAP = FALSE
  rich - cheap = -0.00028 ; RICH excess vs same-DTE -0.00027, HAC t -0.45
  naked-short tail brutal: worst_loss_R -2.7..-4.9, RICH cvar5_pct -0.038, mean/|CVaR5| ~0.005 (gate 0.03)
  RICH year-by-year sign-unstable; drop-worst-5-days flips RICH -0.00021 -> +0.00032 (tail-noise, not edge)
  unconditional NDX overnight short ~ -0.00003 (flat after spread; the SPX-style VRP is ~absent on NDX net of cost)

INTERPRETATION: the SPX cheap-vs-rich diagnostic (the lone t=2.12 bucket out of 9) did NOT survive on an
independent underlying -- it inverted. So it was SPX-window / multiple-comparisons noise, not a structural
effect. Independent replication did its job. Naked short straddle is un-harvestable regardless (tail).

VERDICT: per the LOCKED STOP RULE -> the index-options realized-vs-implied line is SHELVED. No RUT/DJX/SPX
recuts. Deployable iron-fly / forward-log path NOT triggered (replication failed). The harness + the
discipline (no-lookahead, pre-registration, independent replication, real costs, tail accounting) are the
durable assets; the edge was not there.

---

## 2026-06-14 — v0 LOCKED RUN: primary hypothesis NO PASS (variance risk premium dominates)

Ran the locked audit ONCE (Mode A, SPX, protocol_sha 0cbb1594). Consolidated near-ATM SPX EOD chain
2017-2026 (6.3M deduped rows); canonical vol-regime covers 2020-08..2026-04 (validated panel limit);
settlement gate excluded 154/1847 expiries (AM-risk). 1106 bucketed entries (regime+rank both present),
**median DTE = 1** (so this is effectively a ~1-DTE overnight straddle audit).

**FROZEN PRIMARY (VOLATILE x cheap): NO PASS.** n=53, edge vs same-DTE baseline +0.0004, HAC t +0.44
(needs >1.5), concentrated in 2022 (n=34) and negative most other years. The long-vol thesis — cheap
straddles in a volatile regime under-pricing the move — does not hold.

Per the locked ladder: NO PASS on the primary -> **no model, no intraday, no stocks, no MBO, no NDX.**

### Diagnostics (NOT promotable — frozen primary failed; these need their own pre-registration)
- SPX straddles broadly OVER-price the realized move: median realized/implied 0.84; unconditional
  bucketed straddle P&L ~ -0.00008. This is the variance risk premium, exactly where theory predicts ->
  the pipeline is producing economically sane numbers (not a bug).
- Monotonic cheap > mid > rich edge across regimes; the only HAC t>2 bucket is NORMAL x cheap
  (+0.0011, t=2.12). But it is NOT the frozen primary -> promoting it = bucket-shopping. Logged as a
  candidate "avoid expensive straddles / cheap-beats-rich" hypothesis for a FUTURE pre-registered test
  on a fresh/forward basis (the 2020-26 window is now peeked).

### Honest limits of this run
- vol_regime covers only 2020-08..2026-04 (validated panel is 2018-05..2026-04; 504-day warmup). Misses
  2017-2020 incl. the Mar-2020 spike (which also avoids one-event domination).
- ~1-DTE dominance: nearest-expiry in [1,7] is almost always 1 (SPX dailies) -> this is an overnight
  straddle study; a longer-DTE cut is a separate (un-run) question.
- S_expiry = EOD underlying_price (PM-settle proxy); Mode A, NOT live-tradable.

VERDICT: the pre-registered long-vol-by-state thesis is dead on SPX 1-DTE. The variance risk premium is
the dominant feature. Next is Ben/GPT's call: stop, pre-register the cheap-vs-rich diagnostic on a fresh
basis, or forward-log. No options/intraday spend; no model on this window.
