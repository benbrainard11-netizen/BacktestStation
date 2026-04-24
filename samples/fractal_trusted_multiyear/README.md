# Fractal AMD trusted_multiyear sample bundle

A real import bundle for the `Fractal AMD` strategy, `trusted_multiyear` version.
Used by the backend import tests and by the frontend when wiring up the dashboard
against real data.

## Contents

| File | Kind | Source |
|---|---|---|
| `trades.csv` | **Real** | Direct copy of `C:\Fractal-AMD\outputs\trusted_multiyear_trades.csv` (586 trades, 2024-01-02 → 2026-01-09). |
| `equity.csv` | **Derived** | Cumulative `pnl_r` (R-multiples) starting at 0, sampled at each trade's `exit_time`. Drawdown = equity − running peak (negative). |
| `metrics.json` | **Derived** | Computed from `trades.csv`. Dollar PnL per trade is `pnl_r * risk`. Win rate counts `pnl_r > 0`. |
| `config.json` | **Real metadata** | Strategy/version/symbol/session/source, plus the assumptions used when deriving the files above. |
| `live_status.json` | **Placeholder (synthetic)** | Not from a real live session. Marked `_placeholder: true`. Replace before using to validate the live monitor. |

## What "real" means here

- `trades.csv` is the raw Fractal engine output. No columns were removed, renamed, or re-ordered. The backend importer handles its native column names (`entry_time`, `exit_time`, `direction`, `pnl_r`, etc.) via field aliases.
- `equity.csv` and `metrics.json` are **derived deterministically** from `trades.csv` with the derivation documented in `config.json.import_assumptions`. They can be regenerated at any time.
- `live_status.json` is the only synthetic file in the bundle. It exists so the monitor page has something to render; nothing in this file should be treated as a real signal.

## Units

Everything is expressed in R-multiples, not dollars, unless noted:

- `equity` column in `equity.csv` is cumulative R.
- `metrics.json.net_r`, `avg_r`, `avg_win`, `avg_loss`, `max_drawdown` are in R.
- `metrics.json.net_pnl`, `best_trade`, `worst_trade` are in dollars (`pnl_r * risk`).

If the dashboard needs dollar-equity, multiply each trade's `pnl_r` by its `risk` and
cumulate (todo once the frontend needs it).

## Importing

```bash
curl -X POST http://localhost:8000/api/import/backtest \
  -F "trades_file=@samples/fractal_trusted_multiyear/trades.csv" \
  -F "equity_file=@samples/fractal_trusted_multiyear/equity.csv" \
  -F "metrics_file=@samples/fractal_trusted_multiyear/metrics.json" \
  -F "config_file=@samples/fractal_trusted_multiyear/config.json"
```

The symbol (`NQ`) comes from `config.json` since `trades.csv` has no symbol column.
See `backend/tests/test_sample_fractal_import.py` for an automated end-to-end check.
