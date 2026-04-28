"""Fractal AMD trusted strategy plugin (placeholder).

This is the destination for the engine-plugin port of the trusted multi-year
strategy that produced +274R / 40.8% WR over 2024-2026 (586 trades).

The reference implementation is `C:/Fractal-AMD/scripts/trusted_multiyear_bt.py`,
verified to reproduce the bundled `samples/fractal_trusted_multiyear/trades.csv`
exactly when re-run on 2026-04-28 PM.

For an immediate, runnable backtest of the trusted strategy in BacktestStation,
use `backend/scripts/run_trusted_backtest.py`. That script wraps the canonical
implementation and writes its trades to `backend/tests/_artifacts/`.

The engine plugin port (this directory) is intentionally not implemented yet;
see README.md for the work plan and why it's been deferred.
"""
