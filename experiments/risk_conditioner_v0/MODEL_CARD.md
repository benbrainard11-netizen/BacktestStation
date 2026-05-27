# Model Card — risk_conditioner_v0

**Version:** 0
**Status:** Not yet trained (planning phase)
**Owner:** Ben Brainard

## Intended use

Annotate each detector-fired trade candidate from the BacktestStation engine with a sizing multiplier, before the engine submits the OrderIntent. Used for:
- Skipping likely-bad Type A trades
- Downsizing extreme tail-risk Type B trades
- Eventually: prop-firm evaluation pass-rate improvement

## Out-of-scope (v0)

- Creating new trades
- Flipping direction
- Increasing size above base (`size_mult > 1.0`)
- Generic "good vs bad" classification on Type B detectors
- Replacing the existing engine's signal logic

## Inputs

- Detector-fired candidate trades from existing BacktestStation detectors (17 in `backend/app/research/detectors/`, plus the FractalAMD strategy signals)
- MBP-1 quote/trade data, Databento, ES/NQ/YM/RTY .c.0 (~329 trading days, 2025-05-01 → 2026-05-22)
- Processed OHLCV 1m/5m bars, ES/NQ/YM/RTY .c.0
- MBO data, Databento, ES/NQ/YM/RTY .c.0 (~53 trading days, 2026-01-01 → 2026-05-21, backfill in progress)
- Cross-asset bars: ZN, plus ES/NQ/YM/RTY for relative-strength features

## Feature schema

45 features locked. See [`feature_schema.yaml`](feature_schema.yaml) and [`PLAN.md`](PLAN.md) §2.

## Outputs

Per detector-fired trade:
- `p_bad` (Type A only) — probability that MAE_R ≥ 1.0 before target
- `p_tail` (Type B only) — probability that MAE_R > 2.0
- `pred_mae_r_q50`, `pred_mae_r_q80`, `pred_mae_r_q95` — predicted MAE quantiles
- `pred_ttt_sec_q50`, `pred_ttt_sec_q80` — time-to-target quantiles
- `p_target_before_stop` (Type A only)
- `risk_score`, `tail_risk_score` ∈ [0, 1]
- **`size_mult` ∈ {0.0, 0.25, 0.5, 0.75, 1.0}** — the decision

## Training data (Path A)

- Date range: 2025-05-01 → 2026-05-22
- Universe: detector-fired trades with full MBP-1 feature availability
- Final holdout: 2026-03-02 → 2026-05-22 (untouched until fold selection complete)

## Training method

- Type A head: classifier (y_bad) + quantile regressor (y_mae_r) + ttt regressor
- Type B head: classifier (y_tail) + q95 regressor
- Algorithm: LightGBM CUDA (RTX 5080)
- 4 expanding-window walk-forward folds + final holdout (see [`walk_forward.yaml`](walk_forward.yaml))
- Purge + 1-session embargo

## Performance metrics

Not yet trained. Kill / ship thresholds defined in [`PLAN.md`](PLAN.md) §6.

## Limitations / known risks

- **Regime coverage is narrow.** Only ~13 months of training data; no major bear regime sampled.
- **MBO coverage is partial.** ~53 trading days. 5 MBO features are null for trades outside that window; LightGBM handles null natively, but the model effectively learns two regimes.
- **Type B edge fragility.** A naive risk-conditioner could erode the +10,420R FVG zone_reaction edge by over-filtering. Explicit Type B kill criterion: if the headline edge deteriorates materially, the conditioner is killed or restricted to shadow.
- **Continuous-contract roll artifacts.** Databento `.c.0` symbology is not back-adjusted; roll boundaries can create fake MAE / target hits. Roll-day samples are excluded by default.
- **No live signal feedback loop.** v0 is offline-trained and shadow-evaluated. Live-shadow rollout is a stage 1 deliverable post-v0 ship.

## Update / retrain cadence

Not yet defined. Initial cadence proposal: re-train monthly on rolling 13-month window once v0 ships.

## Restrictions / safety

- Must NOT increase position size beyond base (`size_mult ≤ 1.0` always in v0).
- Must NOT flip direction.
- Must NOT silently fallback — missing predictions → `size_mult = 1.0` + explicit logged `risk_model_status`.
- Type B detectors must NOT use a generic good/bad classifier — tail-risk only.
