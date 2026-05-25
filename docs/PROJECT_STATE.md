# Project State

Status date: 2026-05-25

This file is now a compact current-state mirror. Older detailed state snapshots
live in Git history and historical docs; do not use stale April/early-May
sections as operating truth.

## Canonical Current Docs

- `docs/PROJECT_MAP.md`
- `docs/SYSTEM_MAP.md`
- `docs/R2_WAREHOUSE_MAP.md`
- `docs/SCHEMA_SPEC.md`
- `docs/AI_HANDOFF.md`
- `docs/INDEX.md`

## Current BacktestStation State

| Area | State |
|---|---|
| Branch | `assets/expanded-universe-v1` |
| Latest known pushed commit | `7308696 Add MBO R2 warehouse schema support` |
| R2 bucket | `bsdata-prod` |
| R2 inventory | `127084` partitions at last verification |
| MBO in R2 | `112` objects, `17.48 GB`, ES/NQ/RTY/YM, 2026-04-20 through 2026-05-22 |
| Schema support | TBBO, MBP-1, MBO, OHLCV-1m, research/metadata tables |
| Registry support | Dataset snapshots, partition validation, trial registry, lock records |
| Research stack | Detectors, outcomes, feature matrices, strict labels, ML reports |
| Dashboard stack | Data Health, Trials, Candidates, Live Monitor foundations |

## Related Workspaces

| Workspace | State at last cleanup |
|---|---|
| `C:\Users\benbr\InsyncAPP_247` | `ben/personal`, clean, ahead 1 |
| `C:\Users\benbr\InsyncAPP` | tradebot hardening branch, dirty, upstream gone |
| `C:\Users\benbr\InsyncAPP_ben_merge` | main worktree |

The `InsyncAPP` dirty files were intentionally not reset during docs cleanup.

## What Changed Since The Old April Snapshot

- R2 is active and contains current inventory data.
- MBO parquet has been added to the schema and uploaded to R2.
- Trial registry, dataset snapshots, validation reports, and dashboard backend
  infrastructure exist.
- The project is no longer just an imported-results command center; it is the
  research/data warehouse layer for the broader Insync/BacktestStation system.

## Current Gaps

- Some older docs still contain historical paths, old test counts, and old
  phase language.
- `InsyncAPP_247` and other worktrees need a clear worktree map and current
  README.
- Daily MBO mirror automation should be wired so new local MBO partitions sync
  to R2 after download/validation.

