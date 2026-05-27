# tsfm_milk_v0

Calibrated multivariate cross-asset TSFM directional forecaster for ES/NQ/YM/RTY. Embracing the goal: this is built for milking prop-firm evaluations via multi-account copy-trading. v0 = forecaster only; sizing/risk layer is v1.

**Status:** scaffolded, no model trained yet. Phase = `qa.py --audit` (dataset ambiguity audit, PLAN §9).

## Read first

- [`PLAN.md`](PLAN.md) — locked spec. Anything outside is v0.5 or later.
- [`MODEL_CARD.md`](MODEL_CARD.md) — purpose, restrictions, limitations.

## Layout

```
tsfm_milk_v0/
├── PLAN.md                       locked spec
├── README.md                     this file
├── MODEL_CARD.md
│
├── feature_schema.yaml           the 32 input channels
├── labels_and_horizons.yaml      5 horizons + k×σ thresholding
├── walk_forward.yaml             6-fold expanding window + final holdout
│
├── build_dataset.py              load bars → multivariate tensor + labels
├── forecaster.py                 ABC: fit, predict_proba, save, load
├── ttm_forecaster.py             v0 primary: IBM Granite TTM
├── moirai_forecaster.py          v0.5 challenger: Salesforce Moirai-base
├── baseline_lightgbm.py          LightGBM baseline (handcrafted features)
├── baseline_naive.py             marginal class freq baseline
├── train_walkforward.py          training loop, all forecasters × all folds
├── evaluate.py                   metrics + calibration + economic overlay
├── integration.py                write predictions parquet for downstream
├── qa.py                         pipeline tests + dataset ambiguity audit
│
├── out/                          artifacts (gitignored)
└── report/                       per-iteration markdown writeups
```

## Hardware

RTX 5080 (16 GB VRAM). TTM (~1-5M params) leaves massive headroom — can train with large batch + long lookback. Moirai-base (~14M) also fits cleanly.

## How to run (once modules are populated)

```bash
# 0. Sample audit (resolves PLAN §9 ambiguities)
backend/.venv/Scripts/python.exe experiments/tsfm_milk_v0/qa.py --audit

# 1. Build the multivariate dataset (all folds)
backend/.venv/Scripts/python.exe experiments/tsfm_milk_v0/build_dataset.py

# 2. Train all forecasters across all folds
backend/.venv/Scripts/python.exe experiments/tsfm_milk_v0/train_walkforward.py --models naive lightgbm ttm

# 3. Evaluate against kill criteria (PLAN §5)
backend/.venv/Scripts/python.exe experiments/tsfm_milk_v0/evaluate.py
```

## Latest results

None yet. Phase: dataset ambiguity audit (PLAN §9).

## Related

- `experiments/atlas_v0/` — regime classifier, complete (could feed as input feature in v0.3+)
- `experiments/mira_v14_reclaim_confirmation/` — sweep event model
- `experiments/risk_conditioner_v0/` — **PARKED.** Type B framework + meta-labeling approach. Not the direction we're taking.
- `docs/MBO_TRADING_DAY_CONTRACT.md` — trading-day data conventions (used in v0.3+ when MBO/MBP-1 enter)
- `docs/ROADMAP.md` — broader research direction
