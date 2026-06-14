# prop_intraday_resolver_v0

**Status:** SCAFFOLD (created 2026-06-14). Spec + plan + reuse-map + stub skeleton only — **no implementation yet.** Every `.py` here raises `NotImplementedError` and points at the file it should reuse.

**One-liner:** a thin *integration spine* that wires three things this repo already built but never connected end-to-end, into one prop-firm-aware intraday decision system:

```
resolver  →  conditioner  →  governor
(which level-touch  (how hard   (account-safe size
 is worth taking)    to press)   under firm rules)
```

The thesis (Ben's, cleaned up): *At objective intraday levels, event-time order flow tells whether the level holds, breaks, or turns dangerous. The model trades only confirmed branches; the prop governor converts signal quality into account-safe sizing.*

---

## This is NOT a greenfield model

The single most important fact about this project: **~80% of the proposed design already exists in this repo, and Stage 1 already PASSED.** This project does **not** rebuild any of it. It is the missing glue. See [`REUSE_MAP.md`](REUSE_MAP.md) for exact file:line pointers.

| Layer | What it does | Already built in | State |
|---|---|---|---|
| **1–2 Resolver** | event scanner → event-time CKS OFI → triple-barrier hold/break → the OOS judge (day-block bootstrap) | `market_state/intraday/` | **Stage 1 PASSED** (Spearman +0.26 OOS, AUC ~0.60 on PDH/PDL) |
| **3 Conditioner** | detector-fired candidate → `size_mult ∈ {0, .25, .5, .75, 1.0}`; never creates/flips/oversizes | `experiments/risk_conditioner_v0/` | locked spec (45-feat schema, Type A/B heads), **PARKED**, mostly stubs |
| **4 Governor** | account state machine + 6 audited firm rule-sets + pass-rate / survival Monte Carlo | `experiments/sizing_v1/` + `experiments/prop_model_v0/` | working; already optimizes **pass rate, not Sharpe/win-rate** |
| **spine** | pure engine, honest stop-vs-target fills, determinism + lookahead tests, Monte Carlo | `backend/app/backtest/` | working |
| **gamma** | dealer-gamma walls (SPX/NDX/RUT/DJX) + `options_features()` | `experiments/options_signals_v0/`, `experiments/fuhhhhh/` | walls built; **interaction-only, empirically NOT yet validated intraday** |

## What is genuinely net-new (the small part this project actually writes)

1. **Multi-head resolver outputs** — today `market_state` emits binary hold/break. The design wants `P_hold / P_break / P_chop`, `P_target_before_stop`, an R-distribution (`q20/q50/q80`), and a tail head `P(MAE_R > 1R)`. Built on the *existing* harness.
2. **The wiring itself** — `pipeline.py`: events → features → resolver → conditioner → governor, as one deterministic pass.
3. **Intraday bar-grain MTM** — `sizing_v1/account.py` only checks breaches at *trade close*, so an intraday daily-loss-limit breach that recovers by EOD is invisible. A prop governor needs within-day mark-to-market. **Real gap, the design does not call it out.**
4. **Tick-replay fill path** — the core backtest broker resolves on OHLC only (`fill_confidence='conservative'`). Honest tick-by-tick MBP-1 fills already exist in research code (`mira_upgraded_v0/reclaim_entry.py::seq_r`) — reuse, don't rebuild.

## Read next

- [`SPEC.md`](SPEC.md) — the design, corrected against repo reality (data numbers, what's already done, what's overclaimed).
- [`PLAN.md`](PLAN.md) — phased build order with kill criteria and the three binding constraints.
- [`REUSE_MAP.md`](REUSE_MAP.md) — every layer → the exact existing file to import.

## Hard rules inherited from the repo (do not violate)

- **OFI-only event-time model is the non-negotiable judge.** If zones / MBO-depth / cross-index / gamma don't beat it OOS, they are decoration → drop them. (`market_state/INTRADAY_SYSTEM.md`)
- **Feature window ≤ decision time**, enforced by a build-time assert. The deployed Mira gate's "edge" was a lookahead-selection artifact because its features peeked into `[trig, +60s)`. Never again.
- **Clean MBO reader only.** `read_mbo_trading_day()` — never read raw UTC partitions (`docs/MBO_TRADING_DAY_CONTRACT.md`).
- **Honest fills.** Stop wins on ambiguous bars; record `fill_confidence` (`CLAUDE.md` §8).
- **Objective = survival-adjusted EV + low daily-loss tail + pass/reward probability.** Win rate is a diagnostic, never the target.
