# R2 Reader Guide

This is the read-only setup for friends or secondary PCs that need to inspect
the private BacktestStation data lake.

## Credentials

Use an R2 token with:

- Permission: `Object Read only`
- Bucket: `bsdata-prod`
- No write/admin permissions

Set these environment variables in PowerShell:

```powershell
[Environment]::SetEnvironmentVariable("BS_R2_BUCKET", "bsdata-prod", "User")
[Environment]::SetEnvironmentVariable("BS_R2_ENDPOINT", "https://<ACCOUNT_ID>.r2.cloudflarestorage.com", "User")
[Environment]::SetEnvironmentVariable("BS_R2_ACCESS_KEY", "<read-only access key id>", "User")
[Environment]::SetEnvironmentVariable("BS_R2_SECRET", "<read-only secret access key>", "User")
```

Restart PowerShell after setting them.

## Verify Access

From the repo backend directory:

```powershell
cd C:\Users\benbr\BacktestStation\backend
$env:BS_R2_BUCKET=[Environment]::GetEnvironmentVariable('BS_R2_BUCKET','User')
$env:BS_R2_ENDPOINT=[Environment]::GetEnvironmentVariable('BS_R2_ENDPOINT','User')
$env:BS_R2_ACCESS_KEY=[Environment]::GetEnvironmentVariable('BS_R2_ACCESS_KEY','User')
$env:BS_R2_SECRET=[Environment]::GetEnvironmentVariable('BS_R2_SECRET','User')
python -m app.ingest.r2_status --required-universe futures_expanded_v1
```

Good output should show:

- `universe_id: futures_expanded_v1`
- `data/research_events/manifest.json` object check is `OK`
- `data/ml/catalog/ml_dataset_catalog.json` object check is `OK`
- `data/ml/catalog/asset_universe_manifest.json` object check is `OK`
- `Warnings: none`

Machine-readable form:

```powershell
python -m app.ingest.r2_status --required-universe futures_expanded_v1 --json
```

Strict CI-style form:

```powershell
python -m app.ingest.r2_status --required-universe futures_expanded_v1 --strict
```

`--strict` exits non-zero if the lake has stale/missing metadata.

## Current Important Objects

| Key | Purpose |
|---|---|
| `_research_inventory.json` | Current research/ML artifact index. |
| `_inventory.json` | Raw/bar partition index. |
| `data/research_events/manifest.json` | Row counts, feature counts, parquet file list for research events. |
| `data/ml/catalog/asset_universe_manifest.json` | Dataset identity and universe id. |
| `data/ml/catalog/ml_dataset_catalog.json` | Feature matrix, anchor artifact, detector/outcome catalog. |
| `data/ml/catalog/expanded_universe_research_build_report.json` | Expanded-universe build report. |
| `data/ml/levels/opening_gap_level_reactions.parquet` | Universal NDOG/NWOG level-reaction table. |
| `data/ml/levels/fvg_level_reactions.parquet` | Universal FVG level-reaction table. |
| `data/ml/levels/ob_level_reactions.parquet` | Universal order-block level-reaction table. |
| `data/ml/levels/sweep_level_reactions.parquet` | Universal liquidity-sweep level-reaction table. |
| `data/ml/levels/swing_level_reactions.parquet` | Universal swing-pivot level-reaction table. |
| `data/ml/levels/equal_level_reactions.parquet` | Universal equal-high/low level-reaction table. |
| `data/ml/levels/all_level_reactions.parquet` | Combined universal level-reaction table for cross-concept analysis. |
| `data/ml/levels/level_reaction_leaderboard.csv` | Ranked level-family/subtype behavior summary. |
| `data/ml/levels/level_reaction_leaderboard.parquet` | Machine-readable leaderboard equivalent. |

## Download A Manifest

Use this for a quick local copy without exposing secrets:

```powershell
cd C:\Users\benbr\BacktestStation\backend
@'
from pathlib import Path
from app.ingest.r2_client import make_s3_client

s3, bucket = make_s3_client()
key = "data/research_events/manifest.json"
body = s3.get_object(Bucket=bucket, Key=key)["Body"].read()
Path("research_events_manifest.json").write_bytes(body)
print(f"downloaded {key} -> research_events_manifest.json")
'@ | python -
```

## Load Research Events

Research events are partitioned like this:

```text
data/research_events/
  feature_name=<feature>/
    event_year=<year>/
      part-000000.parquet
```

For large analysis, download only the feature/year partitions you need, then
query locally with DuckDB, Polars, or pandas.

Example local DuckDB query after downloading parquet files:

```sql
SELECT feature_name, count(*) AS rows
FROM read_parquet('data/research_events/**/*.parquet')
GROUP BY feature_name
ORDER BY rows DESC;
```

## Download Current Research Artifacts

Use this when a machine needs the latest private R2 research lake locally:

```powershell
cd C:\Users\benbr\BacktestStation\backend
$env:BS_R2_BUCKET=[Environment]::GetEnvironmentVariable('BS_R2_BUCKET','User')
$env:BS_R2_ENDPOINT=[Environment]::GetEnvironmentVariable('BS_R2_ENDPOINT','User')
$env:BS_R2_ACCESS_KEY=[Environment]::GetEnvironmentVariable('BS_R2_ACCESS_KEY','User')
$env:BS_R2_SECRET=[Environment]::GetEnvironmentVariable('BS_R2_SECRET','User')
python -m app.ingest.r2_artifacts_download --groups ml,research_events --dry-run
python -m app.ingest.r2_artifacts_download --groups ml,research_events
```

The downloader only writes files listed in `_research_inventory.json`. It does
not delete local-only files, so old local artifacts may remain until removed
intentionally.

## Safety Rules

- Reader tokens cannot upload, overwrite, or delete.
- Never send write/admin tokens to friends.
- If `r2_status` warns about stale manifests, do not trust row counts until the
  publisher reruns `python -m app.ingest.r2_artifacts --profile core` from the
  latest R2 tooling.
