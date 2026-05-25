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

When daily local downloads are complete, mirror only the newly available
schemas/partitions to R2. For MBO, the desired routine is:

1. Download/produce local MBO parquet.
2. Validate with dry-run.
3. Upload only `--schemas mbo`.
4. Confirm `_inventory.json` still includes non-MBO partitions.
5. Record the run summary.

## Cost Guard

R2 storage is allowed. Databento paid pulls are not allowed without explicit
approval.

If a task requires `databento.metadata.get_cost`, historical downloads, or any
new paid market-data request, stop and ask first.

