# REUSE_MAP — exact existing files each layer imports

This project is glue. Before writing any code, the rule is: **reuse the file in this table; only write new code where the table says "NET-NEW".** Paths are repo-relative. Verified 2026-06-14.

## Layer 1 — events / levels

| Need | Reuse | Notes |
|---|---|---|
| objective level set per trading day | `market_state/intraday/levels.py::build_levels` | PDH/PDL, overnight H/L, session open, OR H/L, prior-week close; ET-segmented, forward-knowledge guarded |
| touch detection + event rows | `market_state/intraday/zone_events.py` | PDH/PDL scanner, REAL + tested |
| vol-scaled zones `[lo,hi]` + confluence | `market_state/intraday/events_v2.py` | ATR-relative tolerance, confluence counting |
| **add gaps / VWAP / VPOC families** | **NET-NEW** in `events.py` | each must earn its seat vs OFI judge |

## Layer 2 — features / labels / resolver / judge

| Need | Reuse | Notes |
|---|---|---|
| event-time CKS OFI, signed vol, queue imbalance | `market_state/intraday/zone_events.py::cks_ofi_inc` (lines 118-142) | the baseline feature set |
| triple-barrier label (outcome AFTER window) | `zone_events.py::label_touch` | `W_OFI` window AFTER touch = no lookahead |
| **the OOS judge** (day-block bootstrap, delta-CI) | `market_state/intraday/hold_break_model.py::block_bootstrap`, `ci`, `fresh_model`, `FEATURE_SETS` | THE non-negotiable judge; add a feature group = add a column + a `FEATURE_SETS` entry |
| signal→outcome PASS/NULL verdict | `market_state/validation/harness.py` | reuse as-is |
| confluence / threshold-robustness sweep | `market_state/intraday/confluence_test.py` | y05..y30 vol-scaled labels |
| honest economic sim at a level | `market_state/intraday/econ_test.py` | ES 1pt=$50 |
| **multi-head outputs** (chop, target-before-stop, R-quantiles, tail) | **NET-NEW** in `labels.py` + `resolver.py` | built on the harness above |
| **build-time lookahead assert** | **NET-NEW** in `features.py::assert_no_lookahead` | encodes the Mira lookahead lesson |

## Layer 3 — risk conditioner

| Need | Reuse | Notes |
|---|---|---|
| 45-feature schema | `experiments/risk_conditioner_v0/feature_schema.yaml` | 8 groups, fully defined |
| size_mult contract `{0,.25,.5,.75,1}` | `experiments/risk_conditioner_v0/PLAN.md §1,§5` + `MODEL_CARD.md` | no create / no flip / no oversize |
| Type A/B separate-head architecture | `risk_conditioner_v0/PLAN.md §4` | do NOT pool A and B |
| walk-forward / purge / embargo | `risk_conditioner_v0/walk_forward.yaml` | 4 folds + holdout |
| MBO tail-risk priors | `risk_conditioner_v0/report/v0_iter0_mbo_validation.md` | `cancel_rate_60s` 5× decile lift (real) |
| **train the heads** | **NET-NEW** in `conditioner.py` | `risk_conditioner_v0` itself is PARKED + stubbed; build Type A first |

## Layer 4 — prop-firm governor

| Need | Reuse | Notes |
|---|---|---|
| account state machine (DLL hard-stop, trailing-DD lock) | `experiments/sizing_v1/account.py`, `firm_rules.py` | |
| position sizing (`vol_targeted`) | `experiments/sizing_v1/sizing.py::size_position` | ATR + conviction + DD-buffer |
| entry gate decision | `experiments/sizing_v1/risk_manager.py::decide` | extend with level-aware skip |
| 6 audited firm rule-sets | `experiments/sizing_v1/config/firms/*.yaml` + `prop_model_v0/funnel_specs.py` | Topstep/Apex/MFFU/Ludic/Tradeify/TPT |
| eval-EV (P(pass) × value − cost) | `experiments/prop_model_v0/eval_ev.py` | sweeps edge level per firm |
| fleet + milkability Monte Carlo | `experiments/sizing_v1/fleet_sim.py`, `monte_carlo_milkability.py` | block-bootstrap, survival % |
| **intraday bar-grain MTM** for within-day DLL breach | **NET-NEW** in `governor.py` | `account.py` only checks at trade close — real gap |

## Spine — backend/app/backtest

| Need | Reuse | Notes |
|---|---|---|
| pure event-driven engine | `backend/app/backtest/engine.py::run` | deterministic, no I/O |
| honest stop-vs-target fills | `backend/app/backtest/broker.py::resolve_active_brackets` | conservative=stop wins |
| determinism + lookahead regression tests | `backend/tests/test_backtest_engine.py` | copy patterns |
| Monte Carlo path resampling | `backend/app/services/monte_carlo.py` | |
| named constants (point value, tick, commission, slippage) | `backend/app/core/config.py`, `broker.py::BrokerConfig` | **import these — never inline** |
| **tick-replay fills** (exact, not conservative) | reuse `experiments/mira_upgraded_v0/reclaim_entry.py::seq_r` | honest tick-by-tick MBP-1 already proven; or extend broker with a ticks param |

## Data

| Need | Reuse | Notes |
|---|---|---|
| clean trading-day reads | `backend/app/data/reader.py::read_mbo_trading_day`, `read_mbp1_trading_day`, `read_bars` | **never read raw UTC partitions** (`docs/MBO_TRADING_DAY_CONTRACT.md`) |
| calendar→trading-day mapping | `backend/app/research/sessions.py::globex_day_for_trading_date` | 18:00 ET → 17:00 ET |
| dealer-gamma walls | `experiments/fuhhhhh/out/walls_v2.parquet` (SPX), `options_signals_v0/out/walls_{ndx,rut,djx}.parquet` | NDX full history; RUT/DJX 2024-06+ only |
| options feature block | `experiments/fuhhhhh/features.py::options_features` | `opt_dist_zg/cw/pw`, ATR-scaled; interaction-only |
| data inventory of record | `docs/DATA_MANIFEST.md` | check before assuming any symbol/date exists |

## Mira (read-only specialist; import, never modify)

| Need | Reuse | Notes |
|---|---|---|
| structural SMT (ES vs NQ/YM/RTY) | `experiments/mira_upgraded_v0/smt_features.py` | needs intraday reference windows for this project |
| sequenced honest R + day-block CI | `experiments/mira_upgraded_v0/reclaim_entry.py::seq_r` | per-symbol point value / tick |
| family-by-family ablation harness | `experiments/mira_upgraded_v0/combine_model.py` | "4 mirages already" — ablate, don't pool |
| ⚠ trap: Mira shorts unrevalidated; gate had a lookahead-selection edge | see `mira_parity_audit`, `mira_short_revalidation` | do not inherit Mira's lookahead |
