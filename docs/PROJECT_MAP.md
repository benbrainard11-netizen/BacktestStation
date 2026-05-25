# BacktestStation Project Map

Status date: 2026-05-25

This is the current front door for BacktestStation. If another doc disagrees
with this map, treat this file, `docs/SYSTEM_MAP.md`, and the code as higher
authority.

## Role

BacktestStation is the research and data brain.

It owns:

- Market-data warehouse schemas and readers.
- Databento ingest, parquet mirroring, and R2 sync tooling.
- Research event detectors, outcomes, feature matrices, and labels.
- Dataset snapshots, validation reports, trial registry, and operator
  dashboards.
- Strategy-lab exports and ML research artifacts.

It should not own:

- Live broker credentials.
- Long-running live trade execution.
- Operator-specific account preferences.
- Secrets or raw/derived data committed to Git.

## Current Branch

Primary working branch:

```text
assets/expanded-universe-v1
```

Current known pushed head when this map was written:

```text
7308696 Add MBO R2 warehouse schema support
```

## Related Workspaces

| Path | Purpose | Current handling |
|---|---|---|
| `C:\Users\benbr\BacktestStation` | Research/data source of truth | Active. Keep clean and pushed. |
| `C:\Users\benbr\InsyncAPP_247` | Personal/live InsyncApp runner worktree | Active. Separate Git worktree on `ben/personal`. |
| `C:\Users\benbr\InsyncAPP` | Dev worktree for InsyncApp tradebot hardening | Dirty at last audit; do not reset without review. |
| `C:\Users\benbr\InsyncAPP_ben_merge` | InsyncApp `main` worktree | Reference/dev app worktree. |
| `C:\Users\benbr\InsyncAPP_market_relay` | Feature worktree | Feature branch. |
| `C:\Users\benbr\InsyncAPP_shared_chart` | Feature/fix worktree | Feature branch. |

## Data Ownership

Git stores code, schema contracts, docs, migrations, manifests, and small
metadata.

R2 and local data roots store actual data:

- Raw Databento archives.
- Raw parquet mirrors.
- Processed bars.
- Research-event parquet.
- Feature matrices.
- Strategy-lab exports.
- Model/research artifacts.

Do not commit large data files. See `docs/R2_WAREHOUSE_MAP.md`.

## Current Data Reality

R2 bucket:

```text
bsdata-prod
```

Latest verified MBO upload:

- Objects: 112
- Size: 17,476,381,452 bytes
- Symbols: ES.c.0, NQ.c.0, RTY.c.0, YM.c.0
- Date range: 2026-04-20 through 2026-05-22
- Inventory total: 127,084 partitions

No Databento API pull was required for that upload; it mirrored local parquet
to R2.

## Current Truth Docs

Read these first:

- `README.md` - short repo entrypoint.
- `docs/PROJECT_MAP.md` - this map.
- `docs/R2_WAREHOUSE_MAP.md` - R2/data warehouse layout and policy.
- `docs/SYSTEM_MAP.md` - deeper component inventory.
- `docs/SCHEMA_SPEC.md` - schema contracts.
- `docs/AI_HANDOFF.md` - instructions for AI/human continuation.
- `docs/TRIAL_REGISTRY_USAGE.md` - research-trial lineage.
- `docs/DATASET_SNAPSHOT_USAGE.md` - dataset snapshot usage.

Treat these as historical/reference unless a current map links to them for a
specific reason:

- `docs/BEN_247_PROMPT_*.md`
- `docs/OVERNIGHT_*.md`
- older `docs/ML_*.md` scoreboards
- one-off session summaries

## Non-Negotiables

- Do not spend Databento API money without explicit user approval.
- Do not overwrite R2 inventories from a partial local disk view.
- Do not train/evaluate on labels or fields that include future outcome data.
- Do not move or delete raw data unless the target path and backup are proven.
- Do not reset dirty worktrees without explicit approval.
- Keep data contracts in docs and code synchronized.

