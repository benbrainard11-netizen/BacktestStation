# BacktestStation Private Cloud Data Lake

This project uses Cloudflare R2 as the private shared data lake.

GitHub remains the place for code, docs, scripts, and small manifests. R2 is
the place for large data: raw bars, historical Databento partitions, research
events, feature matrices, anchor matrices, exports, and experiment outputs.

## Bucket Layout

One private bucket, currently documented as `bsdata-prod`.

| Prefix | Owner | Purpose |
|---|---|---|
| `raw/databento/` | `python -m app.ingest.r2_upload` | Raw Databento parquet partitions. |
| `processed/bars/` | `python -m app.ingest.r2_upload` | Normalized OHLCV bars used by readers. |
| `data/research_events/` | `backend/scripts/ml/export_research_events_parquet.py` then `r2_artifacts` | Shareable parquet snapshot of the `research_events` table. |
| `data/ml/features/` | `python -m app.ingest.r2_artifacts` | Per-feature ML matrices. |
| `data/ml/levels/` | `python -m app.ingest.r2_artifacts` | Universal level-reaction tables and the combined all-level table. |
| `data/ml/anchors/` | `python -m app.ingest.r2_artifacts` | Anchor/snapshot matrices, labels, leaderboards, walk-forward outputs. |
| `data/ml/catalog/` | `python -m app.ingest.r2_artifacts` | Dataset catalogs and asset manifests. |
| `data/research/` | `python -m app.ingest.r2_artifacts` | Curated source datasets, such as macro calendars. |
| `exports/` | `python -m app.ingest.r2_artifacts` | Exact strategy-lab zip packages. |
| `experiments/` | `python -m app.ingest.r2_artifacts --profile experiments` | Optional backtest/GPU result artifacts. |
| `_inventory.json` | `r2_upload` | Raw/bars partition inventory. |
| `_research_inventory.json` | `r2_artifacts` | Research/ML artifact inventory. |

## Machine Roles

| Machine | Role | Token |
|---|---|---|
| `ben-247` | Raw/bar warehouse uploader. | R2 read-write. |
| `benpc` | Research builder/GPU trainer, expanded-universe publisher. | R2 read-write. |
| This PC | Developer/validator. | R2 read-write or read-only depending use. |
| Friends | Readers only. | R2 read-only. |

Never give friends the read-write token.

## Publish Raw/Bars Warehouse

Run from `backend/` or with backend on `PYTHONPATH`:

```powershell
cd C:\Users\benbr\BacktestStation\backend
python -m app.ingest.r2_upload --dry-run
python -m app.ingest.r2_upload
```

This uploads only validated warehouse partitions under `raw/databento/` and
`processed/bars/`.

## Publish Research Events

Prefer parquet over copying a live SQLite database.

```powershell
cd C:\Users\benbr\BacktestStation
python backend\scripts\ml\export_research_events_parquet.py --force
```

This writes:

```text
data/research_events/
  feature_name=<feature>/
    event_year=<year>/
      part-000000.parquet
  manifest.json
```

## Publish ML/Research Artifacts

Dry-run first:

```powershell
cd C:\Users\benbr\BacktestStation\backend
python -m app.ingest.r2_artifacts --profile core --dry-run
```

Upload core research artifacts:

```powershell
python -m app.ingest.r2_artifacts --profile core
```

Upload experiment outputs separately if wanted:

```powershell
python -m app.ingest.r2_artifacts --profile experiments
```

`core` includes `data/ml`, `data/research`, `data/research_events`,
`exports/*.zip`, and `strategy_lab/EXPORT_INDEX.json`.

## Reader Setup

Collaborator machines use read-only credentials:

```powershell
[Environment]::SetEnvironmentVariable("BS_R2_BUCKET", "bsdata-prod", "User")
[Environment]::SetEnvironmentVariable("BS_R2_ENDPOINT", "https://<ACCOUNT_ID>.r2.cloudflarestorage.com", "User")
[Environment]::SetEnvironmentVariable("BS_R2_ACCESS_KEY", "<reader access key>", "User")
[Environment]::SetEnvironmentVariable("BS_R2_SECRET", "<reader secret>", "User")
[Environment]::SetEnvironmentVariable("BS_DATA_BACKEND", "r2", "User")
```

Restart PowerShell after setting env vars.

## Verify The Live Lake

Run the read-only status command from `backend/`:

```powershell
cd C:\Users\benbr\BacktestStation\backend
python -m app.ingest.r2_status --required-universe futures_expanded_v1
```

This checks the R2 inventory, research event manifest, ML catalog, asset
universe manifest, and a sample parquet file. Use `--strict` when a script
should fail on stale/missing metadata.

Friend/collaborator instructions live in `docs/R2_READER_GUIDE.md`.

## What Not To Do

- Do not put R2 secrets in GitHub, Discord, ChatGPT, or screenshots.
- Do not send the read-write token to friends.
- Do not treat GitHub Releases as the main database. They are exact package snapshots only.
- Do not copy a live SQLite DB as the normal sharing method. Export `research_events` to parquet first.
