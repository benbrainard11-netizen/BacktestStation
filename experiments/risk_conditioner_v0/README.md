# risk_conditioner_v0

> **⏸ PARKED 2026-05-27.** This experiment was scaffolded around the Type A / Type B label framework (2026-05-16 discovery, +10,420R FVG zone_reaction headline). The user has flagged the Type B finding as possibly invalidated and considers the underlying labels (OB / FVG / SMT / swing pivot) as too-retail-known to be a durable edge. Active work pivoted to `experiments/tsfm_milk_v0/` (cross-asset TSFM directional forecaster).
>
> **Not deleted because:** the audit + MBO validation scripts work and produced real findings (cancel_rate_60s has 5x decile lift on +5m abs moves). If Type B is re-verified later, or if any future risk-sizing project is started, this scaffold is a head-start.
>
> **To resume:** check out branch `experiments/risk-conditioner-v0`. The full plan is in `PLAN.md`. Last iteration outputs are in `report/` and `out/`.

---

Portfolio risk-conditioner for the BacktestStation engine. Receives detector-fired trade candidates, outputs a sizing multiplier in `{0.0, 0.25, 0.5, 0.75, 1.0}`. Does not create trades, flip direction, or increase size above 1.0.

**Status:** scaffolded, no model trained yet. Phase = ambiguity audit (PLAN §10).

## Read first

- [`PLAN.md`](PLAN.md) — locked spec. Anything outside this is v0.3 expansion work.
- [`MODEL_CARD.md`](MODEL_CARD.md) — high-level model card (intended use, restrictions, limitations).

## Layout

```
risk_conditioner_v0/
├── PLAN.md                     locked spec
├── README.md                   this file
├── MODEL_CARD.md
│
├── detector_families.yaml      detector → {A, B} mapping
├── feature_schema.yaml         the 45 locked features
├── walk_forward.yaml           expanding-window folds
├── stop_defaults.yaml          per-symbol fallback stops
│
├── build_trade_universe.py     candidate trades from detector fires
├── build_features.py           the 45-feature builder
├── build_labels.py             MAE_R, y_bad, y_tail, y_ttt
├── train_walkforward.py        Type A + Type B heads
├── evaluate.py                 statistical + economic metrics
├── integration.py              OrderIntent adapter
├── qa.py                       lookahead / alignment / dispatch tests
│
├── out/                        parquet artifacts (gitignored)
└── report/                     per-iteration writeups
```

## How to run (once modules are populated)

```bash
# 1. Sample-count + ambiguity audit (read-only, no model training)
backend/.venv/Scripts/python.exe experiments/risk_conditioner_v0/qa.py --audit

# 2. Build the candidate-trade universe
backend/.venv/Scripts/python.exe experiments/risk_conditioner_v0/build_trade_universe.py

# 3. Build labels and features
backend/.venv/Scripts/python.exe experiments/risk_conditioner_v0/build_labels.py
backend/.venv/Scripts/python.exe experiments/risk_conditioner_v0/build_features.py

# 4. Train baseline ladder
backend/.venv/Scripts/python.exe experiments/risk_conditioner_v0/train_walkforward.py --ladder all

# 5. Evaluate against kill criteria (PLAN §6)
backend/.venv/Scripts/python.exe experiments/risk_conditioner_v0/evaluate.py
```

## Latest results

None yet. Phase: ambiguity audit (PLAN §10).

## Related

- `experiments/atlas_v0/` — regime classifier, complete
- `experiments/mira_v14_reclaim_confirmation/` — sweep event model, active
- `experiments/mbo_features_v0/` — earlier MBO feature exploration; **scan.py is reusable** for v0 MBO features
- `docs/ROADMAP.md` — broader research direction
- `docs/ARCHITECTURE.md` — engine purity rules
