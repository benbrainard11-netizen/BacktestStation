# SPEC - move_env_gate_v0

## Purpose

Build the first practical version of the pasted research direction:

`more data -> better state definition -> better gating/conditioning`

This experiment is not a replacement for BacktestStation Phase 1 and does not
change the app shell. It is an isolated research lane under `experiments/`.

## Core Question

Do not ask, "Can I predict ES direction?"

Ask:

> When an existing setup or objective event fires, is the next window worth
> trading, or is it a bad environment to skip/downsize?

## v0 Inputs

Start from an existing event table, not raw Databento ingestion:

- default: `experiments/prop_intraday_resolver_v0/out/dataset_ES_trading_day.parquet`
- required forward columns: `mfe_R`, `mae_R`, `realized_R`
- accepted causal feature blocks: geometry, MBP-1 event-time flow, cross-index flow

MBO, options, and stock breadth are future feature blocks. They are not assumed
useful until they improve OOS trade diagnostics.

## v0 Targets

- `MOVE`: either favorable or adverse 1R barrier touched.
- `FAVORABLE_MOVE`: favorable 1R barrier touched.
- `BAD_ENV`: adverse 1R barrier won first.
- `CHOP`: neither barrier touched before timeout.

The main model pair is:

- Model A: `p_move`
- Model B: `p_bad_env`

The v0 gate score is:

`p_move - p_bad_env`

## v0 Evaluation

Use a time split, train thresholds only, and block ablations.

Feature blocks:

1. geometry
2. OFI only
3. MBP-1
4. cross-asset
5. MBP-1 + cross-asset
6. all v0

Primary comparison:

`baseline detector population` vs `baseline + model gate`

Measured by:

- mean R
- profit factor
- max drawdown
- bad-environment rate
- skipped-vs-selected mean R

AUC is not a success metric. It is only a diagnostic.

## Strategy Table Extension

The experiment also has a strategy-output path:

`build_strategy_event_table.py -> evaluate_strategy_gate.py`

This is for the "actual detector trades" question:

> Does a simple skip gate improve the strategy's own trade population?

Current normalized sources:

- Fractal AMD trusted multiyear trades.
- Mira recent live-replay candidates, quarantined by default.
- Mira Jan replay trades, quarantined by default.

These sources are evaluated separately. Do not pool them into one model unless a
future spec proves they share a decision surface.

Mira quarantine rule: frozen-gate/replay rows that depend on post-trigger
bookproxy features are not eligible for default model training or conclusions.
Use them only with an explicit forensic flag until a legal feature rebuild exists.

## Guardrails

- No TSFM until a simple tabular gate improves OOS economics.
- No feature window can occur after the decision time.
- Do not add options/stocks/MBO as a monolith. Add one block, then ablate.
- Do not treat the parked OFI resolver as a trading edge; this lane only asks
  whether move/bad-environment conditioning is useful.
- Preserve source config and generated manifests for every event table.
