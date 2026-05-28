# sizing_v1

The sizing/risk layer for the milk-v1 model. Takes calibrated probability outputs and converts them into per-account contract counts, simulates prop firm evaluation accounts, and reports the milking metric: **percent of accounts that pass.**

This is the "money layer." The model gives signal; this gives risk discipline.

**Status:** scaffolded, no simulator built yet. Phase = ambiguity audit (PLAN §12: per-firm rule numbers).

## Read first

- [`PLAN.md`](PLAN.md) — locked spec. Anything outside is v1.5+ work.
- [`MODEL_CARD.md`](MODEL_CARD.md) — purpose, restrictions, limitations.

## Inputs

```
Model predictions:    ../tsfm_milk_v0/out/predictions/lightgbm_ensemble/
                       (the milk-v1 iter-1 winner: +$98k aggregate)

Bars for execution:   D:/data/processed/bars/timeframe=1m/

Firm rules:           config/firms/*.yaml
Strategy config:      config/strategy_v0.yaml
```

## Active cells (initial deployment)

Per milk-v1 iter-1 honest results:

```
NQ.c.0 × h_60m   ← carries most of the edge (+$43k)
RTY.c.0 × h_90m  ← second strongest (+$19k)
ES.c.0 × h_15m   ← small but positive (+$11k)
YM.c.0 × h_30m   ← small but positive (+$8k)

240m horizon: NOT TRADED (loses for everyone, drop from v0 deployment)
```

## Firms targeted

Topstep, Tradeify, Apex, MFFU, Ludic, TPT — six configs in `config/firms/`. Topstep gets locked first (best-documented rules). Others fill in as rule numbers are confirmed.

## How to run (once modules are populated)

```bash
# 0. Ambiguity audit (per-firm rule confirmation)
backend/.venv/Scripts/python.exe experiments/sizing_v1/qa.py --audit

# 1. Simulate one firm × 100 accounts
backend/.venv/Scripts/python.exe experiments/sizing_v1/simulator.py \
    --firm topstep_50k --n-accounts 100 --strategy strategy_v0

# 2. Simulate all firms
backend/.venv/Scripts/python.exe experiments/sizing_v1/multi_account_router.py --all-firms

# 3. Pass-rate report
backend/.venv/Scripts/python.exe experiments/sizing_v1/evaluate_sizing.py
```

## Layout

```
sizing_v1/
├── PLAN.md, README.md, MODEL_CARD.md
│
├── config/
│   ├── strategy_v0.yaml
│   └── firms/                       per-firm rule configs
│
├── account.py                       Account state machine
├── firm_rules.py                    rule engines per firm
├── sizing.py                        probability → contract count
├── risk_manager.py                  take/skip decision
├── simulator.py                     walk-forward trade simulation
├── multi_account_router.py          N-account parallel sim
├── evaluate_sizing.py               pass rate + milking math
├── qa.py                            lookahead + state consistency tests
│
├── out/                             artifacts (gitignored)
└── report/                          per-iteration writeups
```

## Related

- `experiments/tsfm_milk_v0/` — the upstream model (now milk-v1 iter-1, tagged v0_complete_iter1)
- `experiments/risk_conditioner_v0/` — PARKED sibling experiment
- `docs/MBO_TRADING_DAY_CONTRACT.md` — data conventions (relevant if v1.5 adds MBO-aware execution)

## The killer metric

After all this is built, the question this layer answers is:

> If we run 100 Topstep $50K Combine evaluation accounts using the milk-v1 LightGBM ensemble's signals on NQ-60m, RTY-90m, ES-15m, YM-30m, **what fraction pass the evaluation?**

That number × N evals × funded account value − N × eval fee = the milking math. **Pass rate is what matters. Not Sharpe. Not AUC. Pass rate.**
