# fuhhhhh — options-informed intraday ES objective model

Started 2026-06-12. Origin: a GPT-5.5 research spec (options define the battlefield,
futures confirm the trigger), adapted to this repo's data reality and prior findings.

## The question

Not "will price go up?" but:

> Given current options positioning, nearby objective levels, session context, and
> futures order flow — what is the probability price reaches Objective A before
> Invalidation B within N minutes?

Universe: **SPX options → ES futures**, intraday (RTH, 5-min decision grid), day-flat,
prop-firm-aware. One causal chain, not five markets.

## Why this isn't a re-run of the graveyard

This repo has already tested ~12 gamma/options constructions and killed nearly all of
them — **at the daily / next-day grain** ([PRIOR_ART.md](PRIOR_ART.md) is the binding
ledger). The standing verdict there: SPX options data carries no incremental *next-day
index-direction* information beyond price/vol/cross-asset. The technically-open door
named in that verdict is **intraday options flow** — and intraday SPX data (5-min
greeks, 0DTE flow panels, per-minute GEX) exists locally for 2025-05 → 2026-06,
exactly overlapping ES MBP-1 coverage. That intraday, objective-first construction is
where this experiment lives. Anything that smells like a killed construction does not
get re-run without a materially new mechanism (SPEC rule 11).

## Files

| File | What |
|---|---|
| [SPEC.md](SPEC.md) | The constitution: phases, hard rules, controls, verdict discipline. Read first. |
| [PRIOR_ART.md](PRIOR_ART.md) | Graveyard ledger — what was already tested and killed/contaminated/open. |
| [DATA.md](DATA.md) | Concrete local data inventory, joint coverage window, loaders. |
| [common.py](common.py) | Shared paths, economics constants, windows, no-lookahead assert. |
| [phase0_sanity.py](phase0_sanity.py) | Phase 0: artifact existence, coverage, one-day alignment check. |
| [data_io.py](data_io.py) | Bars/panels/basis/ATR loaders (causal by construction). |
| [features.py](features.py) | opt_ + fut_ feature blocks at decision time t. |
| [objectives_labels.py](objectives_labels.py) | Objective engine, geo_ block, race labels, realized R. |
| [build_dataset.py](build_dataset.py) | Dataset builder (dev only) + manifest + lookahead asserts. |
| [model_v0.py](model_v0.py) | WF LightGBM, 4 embedded ablations, control, EV trade layer, report. |
| [LEDGER.md](LEDGER.md) | Every test's construction, result, verdict, diagnosis. |
| HOLDOUT_LEDGER.md | (created at first read) sealed-holdout read ledger — budget: 2 lifetime reads. |

## Status

- **Iterations 1, 2A, 2B DONE 2026-06-12** (LEDGER P2–P4). Trajectory: v1 −0.088 →
  2A (nested calibration + payoff cap) −0.036 → 2B (economic objective filters,
  dataset v2_c006) **+0.016 net / +0.053 gross, PF 1.05** — first positive-net
  candidate cell, with REAL side-picking skill (+0.097 vs same-rows uninformed
  counterfactual; drift autopsy clean) and it survives 1-min delayed entry. NOT yet
  stable: flips on drop-best-5-days, folds+ 2/5 → no victory declared. **Iteration 3
  registered: 90-min barrier (timeouts 67–81% on v2), prop risk shell vs day
  concentration (top-K/day), options un-quarantine as conditional interactions
  (E/F cells went positive on v2 — options waking up at longer horizons).**
- New since v0: `eval_lib.py` (timeout-patched EV + full diagnostics), `mbp_features.py`
  + `build_mbp_features.py` (31-feature MBP-1 block, cached), `model_v1.py` (ablations
  A–F + controls G/H + delayed-entry I), `diag_info_edge.py`.
- ThetaData deep backfill still running in the background (see DATA.md §4).
- Run anything with `backend\.venv\Scripts\python.exe` (has lightgbm 4.6.0; `.venv-ml` does NOT).
