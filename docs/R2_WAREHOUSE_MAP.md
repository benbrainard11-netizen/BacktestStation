# R2 Warehouse Map

Status date: 2026-05-25

R2 is the private cloud warehouse for BacktestStation data. It is not a code
repo and should not contain source-code logic.

## Bucket

```text
bsdata-prod
```

Access is private. Use separate tokens:

- Write token: only on trusted uploader machines.
- Read token: collaborators and consumer machines.

Never paste permanent secrets into docs or commits.

## Storage Policy

R2 stores data and manifests. Git stores code and contracts.

R2 should hold:

- Raw market-data parquet mirrors.
- Processed bars.
- Research-event parquet.
- ML feature matrices.
- Strategy-lab exports.
- Inventory/catalog files.
- Validation and dataset artifacts when they are too large for Git.

Git should hold:

- Schema specs.
- Upload/download tools.
- Migration code.
- Snapshot metadata schema.
- Small docs and reports.

## Current Verified Inventory

Last verified during the MBO upload pass:

```text
total partitions: 127084
mbo partitions:   112
mbo bytes:        17476381452
```

MBO scope:

| Field | Value |
|---|---|
| Symbols | `ES.c.0`, `NQ.c.0`, `RTY.c.0`, `YM.c.0` |
| Dates | `2026-04-20` through `2026-05-22` |
| Objects | `112` |
| Size | `17.48 GB` decimal / `16.28 GiB` |
| Prefix | `raw/databento/mbo/` |

This was a local-to-R2 mirror only. It did not call Databento historical APIs.

## Prefix Layout

Canonical market-data prefixes:

```text
raw/databento/tbbo/symbol={SYMBOL}/date={YYYY-MM-DD}/part-000.parquet
raw/databento/mbp-1/symbol={SYMBOL}/date={YYYY-MM-DD}/part-000.parquet
raw/databento/mbo/symbol={SYMBOL}/date={YYYY-MM-DD}/part-000.parquet
processed/bars/timeframe=1m/symbol={SYMBOL}/date={YYYY-MM-DD}/part-000.parquet
```

Research/artifact prefixes:

```text
data/research_events/
data/ml/
data/ml/features/
data/ml/levels/
exports/
```

Inventory files:

```text
_inventory.json
_research_inventory.json
```

## Upload Rules

Use schema-targeted uploads when the local machine only has part of the lake.
The uploader must merge target-schema inventory into existing R2 inventory
instead of rebuilding `_inventory.json` from local disk only.

Safe pattern:

```powershell
python -m app.ingest.r2_upload --schemas mbo
```

Dry-run first:

```powershell
python -m app.ingest.r2_upload --dry-run --schemas mbo
```

## Daily Mirror Target

When daily local MBO parquet is available, mirror only MBO to R2. This path
does not call Databento; it only reads local parquet under `BS_DATA_ROOT`.

Manual dry-run:

```powershell
cd C:\Users\benbr\BacktestStation\backend
python -m app.ingest.mbo_r2_mirror --dry-run
```

Manual upload:

```powershell
cd C:\Users\benbr\BacktestStation\backend
python -m app.ingest.mbo_r2_mirror
```

Install the daily scheduled task:

```powershell
cd C:\Users\benbr\BacktestStation
powershell -ExecutionPolicy Bypass -File scripts\install_mbo_r2_mirror_task.ps1
```

The installed task is:

```text
BacktestStationMboR2Mirror
```

It runs `python -m app.ingest.mbo_r2_mirror`, which:

1. Requires local MBO parquet to already exist under `BS_DATA_ROOT`.
2. Validates local MBO with `r2_upload --dry-run --schemas mbo`.
3. Aborts if any MBO partition is refused.
4. Uploads only `--schemas mbo`.
5. Merges MBO entries into existing `_inventory.json` so non-MBO inventory is
   preserved.
6. Records logs under `{BS_DATA_ROOT}/logs/`.

Log files:

```text
{BS_DATA_ROOT}/logs/mbo_r2_mirror.log
{BS_DATA_ROOT}/logs/mbo_r2_mirror_runs.json
{BS_DATA_ROOT}/logs/r2_upload.log
{BS_DATA_ROOT}/logs/r2_upload_runs.json
```

## Cost Guard

R2 storage is allowed. Databento paid pulls are not allowed without explicit
approval.

If a task requires `databento.metadata.get_cost`, historical downloads, or any
new paid market-data request, stop and ask first.
