# Pre10

> Pre10 is a live/paper trade-outcome dataset, not one of the 12 research detector feature matrices.

## What it is

Pre10 currently refers to the VP continuation strategy data pulled from paper/live trade logs and normalized into a labeled trade-outcome table.

This dashboard exists so strategy outcome data can sit next to research feature data, but it should not be confused with the detector snapshots. The detector database is concept/event research; Pre10 is trade-level outcome research.

## Where the code lives

| Component | Path |
|---|---|
| Trade outcome builder | `backend/app/research/build_labeled_outcomes.py` |
| Expected output parquet | `D:\data\research\labeled_outcomes\trades_v1.parquet` |
| Morning report | `docs/MORNING_REPORT_2026-05-08.md` |
| Live stats | `./stats.md` |

## What the dataset records

Each row is one trade or paper trade with:

- signal identity and source
- strategy name
- signal time
- side and prices
- risk and contracts
- Pre10-specific fields such as router probability
- realized R and exit reason
- bar context available at signal time

## ML note

This dataset is currently small. It is useful for validating the trade-outcome pipeline, but not enough to train serious models. The high-leverage future work is logging richer signal-time features and adding backtest-derived rows.
