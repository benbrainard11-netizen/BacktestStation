# AI Handoff

Status date: 2026-05-25

Use this file when an AI agent or human is picking up the workspace cold.

## Start Here

1. Check repo state.

```powershell
cd C:\Users\benbr\BacktestStation
git status --short --branch
```

2. Read the current maps.

```text
README.md
docs/PROJECT_MAP.md
docs/R2_WAREHOUSE_MAP.md
docs/SYSTEM_MAP.md
docs/SCHEMA_SPEC.md
```

3. If the task touches InsyncApp, check worktrees.

```powershell
cd C:\Users\benbr\InsyncAPP
git worktree list
git status --short --branch
```

4. Run the workspace health helper from BacktestStation when available.

```powershell
cd C:\Users\benbr\BacktestStation
.\scripts\workspace_health.ps1
```

5. If the task is about MBO/R2 freshness, use the dedicated mirror command.

```powershell
cd C:\Users\benbr\BacktestStation\backend
python -m app.ingest.r2_freshness_audit
python -m app.ingest.mbo_r2_mirror --dry-run
python -m app.ingest.mbo_r2_mirror
```

## Machine/Repo Roles

| Workspace | Role |
|---|---|
| `BacktestStation` | Research database, feature engineering, R2 sync, validation, trial registry |
| `R2 bsdata-prod` | Private cloud data warehouse |
| `InsyncAPP_247` | Personal/live InsyncApp runner worktree |
| `InsyncAPP` | Dev worktree, currently dirty at last audit |
| `InsyncAPP_ben_merge` | Main-branch InsyncApp worktree |

## Current Guardrails

- Do not spend Databento API money unless Ben explicitly approves that exact
  pull.
- Do not reset or delete dirty Git worktrees without explicit approval.
- Do not edit live broker/runtime secrets into Git.
- Do not treat old prompt/result docs as current truth unless they are linked
  from `docs/PROJECT_MAP.md` or `docs/SYSTEM_MAP.md`.
- Do not run live trade execution without reading the current runbook and
  confirming kill-switch/account state.
- Do not overwrite R2 inventories from partial local data.
- For MBO cloud sync, prefer `python -m app.ingest.mbo_r2_mirror` or
  `python -m app.ingest.r2_upload --schemas mbo`; do not use a full inventory
  rebuild from a partial machine.

## Known State At Last Cleanup

BacktestStation:

```text
branch: assets/expanded-universe-v1
status: clean and synced
latest known commit: 7308696 Add MBO R2 warehouse schema support
```

InsyncApp worktrees:

```text
InsyncAPP_247: ben/personal, clean, ahead 1 at last audit
InsyncAPP: tradebot/rithmic-adapter-hardening-v1, dirty, upstream gone
InsyncAPP_ben_merge: main worktree
```

R2:

```text
bucket: bsdata-prod
inventory partitions: 127084
mbo objects: 112
mbo bytes: 17476381452
```

## How To Decide Where Work Belongs

Put work in BacktestStation when it is about:

- Data schemas.
- R2 upload/download/catalog.
- Detectors, labels, feature matrices.
- Dataset snapshots and validation.
- Research reports.
- ML dataset exports.

Put work in InsyncApp when it is about:

- User-facing execution UI.
- Live/paper tradebot engine.
- Broker/account runtime config.
- App-side dashboards consuming BacktestStation/R2 artifacts.

Put data in R2/local data roots, not Git.
