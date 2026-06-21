# move_env_gate_v0

Started 2026-06-19 on branch `codex/move-env-gate-v0`.

This is the small experiment requested by the pasted note:

1. Build a clean event/state table.
2. Predict whether the next window is worth trading.
3. Predict bad environments that should be skipped or downsized.
4. Ablate feature blocks before adding bigger models.

It deliberately does **not** start with a TSFM or a giant multi-market model.
The first runnable target is a boring gate:

`setup/event fires -> p_move and p_bad_env -> take/skip/downsize diagnostic`

## Current v0

Default source:

`experiments/prop_intraday_resolver_v0/out/dataset_ES_trading_day.parquet`

That source already has event-time MBP-1/cross-index features and forward
entry-relative labels from the parked resolver experiment. This lane reuses it
as a causal seed table, then asks a narrower question:

> Can simple feature blocks filter the worst candidate environments OOS?

## Run

```powershell
backend\.venv\Scripts\python.exe experiments\move_env_gate_v0\build_event_table.py
backend\.venv\Scripts\python.exe experiments\move_env_gate_v0\evaluate_gate.py
```

To point the same idea at actual strategy outputs:

```powershell
backend\.venv\Scripts\python.exe experiments\move_env_gate_v0\build_strategy_event_table.py
backend\.venv\Scripts\python.exe experiments\move_env_gate_v0\evaluate_strategy_gate.py
```

The strategy table builder currently normalizes:

- Fractal AMD trusted multiyear trades (`586` trades, real sample bundle).

Mira exports are quarantined by default because the frozen Mira gate/replay path
has known lookahead risk from post-trigger/bookproxy features. They are available
only for forensic inspection:

```powershell
backend\.venv\Scripts\python.exe experiments\move_env_gate_v0\build_strategy_event_table.py --include-quarantined-mira
backend\.venv\Scripts\python.exe experiments\move_env_gate_v0\evaluate_strategy_gate.py --include-quarantined
```

The strategy evaluator runs per `source_kind`, refuses to model thin sources,
and skips quarantined rows unless explicitly asked.

Outputs are written to `experiments/move_env_gate_v0/out/`, which is ignored by
the repo's existing `out/` rule.

## Labels

- `y_move`: either favorable or adverse 1R barrier was touched.
- `y_favorable_move`: favorable 1R barrier was touched.
- `y_bad_env`: adverse 1R barrier won first.
- `y_chop`: neither barrier was touched before timeout.

These are converted from existing forward columns (`mfe_R`, `mae_R`,
`realized_R`). The builder does not create new future-looking features.

## Feature Blocks

- `geometry`: level side and candidate direction.
- `ofi_only`: the minimal event-time OFI judge.
- `mbp1`: OFI, top-book imbalance, signed trade flow.
- `cross_asset`: NQ/RTY/YM confirmation and dispersion.
- `mbp1_cross`: MBP-1 plus cross-index context.
- `all_v0`: all causal v0 blocks.

## Verdict Rule

AUC is only a diagnostic. The gate earns attention only if the selected OOS
population improves trade diagnostics versus the baseline detector population:

- mean R
- profit factor
- max drawdown
- bad-environment rate
- skipped population worse than selected population

If it only improves AUC and not R/tail behavior, it is not an edge.
