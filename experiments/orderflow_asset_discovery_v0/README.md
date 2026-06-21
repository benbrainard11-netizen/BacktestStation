# orderflow_asset_discovery_v0

Goal: rank the full futures universe by whether MBP-1 orderflow is worth modeling.

This is a scouting layer, not a trading system. It reads mirrored MBP-1 parquet from:

```text
D:/data/raw/databento/mbp-1/symbol=<SYM>/date=<YYYY-MM-DD>/part-000.parquet
```

and writes small 15-minute bucket features plus symbol-level reports under `out/`.

## Run After Mirror

```powershell
backend\.venv\Scripts\python.exe experiments\orderflow_asset_discovery_v0\scan_mbp1_assets.py `
  --start 2025-05-28 `
  --end 2026-05-27
```

Smoke test:

```powershell
backend\.venv\Scripts\python.exe experiments\orderflow_asset_discovery_v0\scan_mbp1_assets.py `
  --symbols ES.c.0 CL.c.0 `
  --limit-days 2
```

## Outputs

- `out/buckets_15m/symbol=<SYM>/date=<YYYY-MM-DD>.parquet`
- `out/daily_summary.csv`
- `out/symbol_scoreboard.csv`
- `report/asset_discovery_summary.md`

## What The Score Means

`discovery_score` is a quick triage score from liquidity, spread cost, coverage, and simple next-bucket orderflow correlations. It is not a P&L result. Good symbols from this report should then get a proper bars-only vs bars+orderflow walk-forward test with explicit costs.
