# ML Regime Context

_Generated 2026-05-14._

This layer adds market regime context from completed interval true-range events.
It answers: "What was the most recent completed Asia/London/NY/day/week range
state before this anchor fired?"

## What It Uses

- `itr.parquet`: completed interval true range events.
- Prefix added to snapshot matrices: `regime.*`.

## Regime Types

| Type | Meaning |
|---|---|
| `any_itr` | Most recent completed interval of any ITR type. |
| `asia_itr` | Most recent completed Asia session interval. |
| `london_itr` | Most recent completed London session interval. |
| `ny_itr` | Most recent completed New York session interval. |
| `daily_itr` | Most recent completed Globex day interval. |
| `weekly_itr` | Most recent completed Globex week interval. |

## Feature Shape

Each matrix receives `156` `regime.*` feature columns:

- minutes since the last completed interval
- last range and true range
- last close location inside the interval
- previous-10-interval range percentile
- bullish/bearish direction flags
- expansion/compression flags
- counts of completed intervals over 24h
- counts of expansion/compression intervals over 7d

Each feature is split by:

- `same_primary`: only the anchor symbol
- `any_symbol`: cross-market context across symbols

## Zero-Look-Ahead Rule

ITR events are timestamped on the final minute of the completed interval. The
builder shifts them forward by one minute before assigning features, so the
closed interval is not visible before it actually closes.

## Built Matrices

| Matrix | Rows | Columns | Audit |
|---|---:|---:|---|
| `sweep_snapshots_xctx_fvggeom_obgeom_liqgeom_regime.parquet` | 52,946 | 3,238 | clean |
| `smt_previous_day_snapshots_xctx_fvggeom_obgeom_liqgeom_regime.parquet` | 4,676 | 3,179 | clean |

## Builder

```powershell
python backend\scripts\ml\build_regime_context.py
```

Use `--matrix`, `--schema`, `--output`, `--schema-output`, and
`--context-output` to apply it to another anchor matrix.
