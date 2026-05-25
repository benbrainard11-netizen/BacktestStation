# BacktestStation

Local-first research, data, validation, and ML infrastructure for personal
futures research.

Status date: 2026-05-25

## Current Role

BacktestStation is the research and data brain. It owns:

- Databento ingest and parquet warehouse schemas.
- Cloudflare R2 upload/download/catalog tooling.
- Research events, detectors, outcomes, strict labels, and feature matrices.
- Dataset snapshots, partition validation, and trial registry tables.
- Operator dashboards for data health, trials, candidates, and live-monitor
  state.
- Strategy-lab exports and ML research reports.

Live/paper execution belongs in InsyncApp. Actual data files belong in local
data roots or R2, not Git.

## Start Here

Read these first:

- [Project Map](docs/PROJECT_MAP.md)
- [Documentation Index](docs/INDEX.md)
- [R2 Warehouse Map](docs/R2_WAREHOUSE_MAP.md)
- [System Map](docs/SYSTEM_MAP.md)
- [Schema Spec](docs/SCHEMA_SPEC.md)
- [AI Handoff](docs/AI_HANDOFF.md)

Older prompt, overnight, and ML result docs are historical unless one of the
current maps links to them for a specific reason.

## Current Branch

Primary working branch:

```text
assets/expanded-universe-v1
```

Last known pushed head when this README was updated:

```text
7308696 Add MBO R2 warehouse schema support
```

## Data

Local warehouse root is configured by `BS_DATA_ROOT`.

Private cloud warehouse:

```text
R2 bucket: bsdata-prod
```

Latest verified R2 state:

- Inventory partitions: `127084`
- MBO objects: `112`
- MBO size: `17.48 GB` decimal / `16.28 GiB`
- MBO symbols: `ES.c.0`, `NQ.c.0`, `RTY.c.0`, `YM.c.0`
- MBO dates: `2026-04-20` through `2026-05-22`

See [R2 Warehouse Map](docs/R2_WAREHOUSE_MAP.md) for upload rules.

## Stack

- Backend: FastAPI, Python 3.12, SQLAlchemy, SQLite, PyArrow, Pandas
- Frontend: Next.js, TypeScript, Tailwind
- Data: Databento DBN/parquet, Hive partitions, Cloudflare R2
- Validation: dataset snapshots, partition validation reports, trial registry
- ML/research: strict labels, anchor matrices, walk-forward reports

## Quick Checks

```powershell
git status --short --branch
.\scripts\workspace_health.ps1
```

MBO-to-R2 manual mirror:

```powershell
cd backend
python -m app.ingest.r2_freshness_audit
python -m app.ingest.r2_inventory_repair --schemas mbo --dry-run
python -m app.ingest.mbo_r2_mirror --dry-run
python -m app.ingest.mbo_r2_mirror
```

Backend tests are run from the repo root or `backend/` depending on the target
suite. Use focused tests for the area you changed.

## Guardrails

- Do not spend Databento API money without explicit approval.
- Do not commit raw or derived warehouse data.
- Do not overwrite R2 inventory from a partial local disk view.
- Do not use future/outcome fields as model features.
- Do not reset dirty worktrees without explicit approval.
