# Branch audit — 2026-04-24

> Generated during the autonomous session. Delete this file once you've reviewed and run any cleanup commands you agree with.

I did NOT delete any branches. Every cleanup below requires Ben to run the command.

## Summary

| Category | Count | Action |
|---|---|---|
| Active in-flight (this session's work) | 4 | Keep |
| Fully merged to `main` | 30 | Safe to delete |
| Stale and divergent (looks abandoned) | 1 | Investigate before deleting |

## Active in-flight branches — KEEP

These contain the work from today's session. Stack order (each builds on the previous):

```
main
└─ task/strategy-editor-pipeline   (+4 commits — archive lifecycle + dossier polish + docs)
   └─ feat/research-workspace      (+7 from main — Notes Workspace)
      └─ feat/experiment-ledger    (+11 from main — Experiments backend + UI scaffold + doc breadcrumbs)
         └─ feat/prompt-generator  (+15 from main — AI Prompt Generator + UX polish + run-detail notes)
```

## Fully merged to `main` — safe to delete

All of these have zero commits ahead of `main`. Their work is already on `main` via a merge or rebase.

```
review/frontend-cleanup
review/frontend-import
task/add-roadmap
task/backend-read-api
task/backtest-csv-export
task/compare-r-histogram
task/config-snapshot-display
task/data-quality-candles
task/delete-backtest-runs
task/fractal-import-compat
task/frontend-backtests-compare
task/frontend-backtests-detail
task/frontend-backtests-filters
task/frontend-backtests-list
task/frontend-import-form
task/frontend-journal-notes
task/frontend-monitor-live
task/frontend-r-histogram
task/frontend-replay
task/frontend-strategies
task/frontend-types-migration
task/openapi-typegen
task/phase-2-closeout
task/prop-firm-simulator
task/real-command-center
task/rename-backtest-runs
task/run-tags
task/sample-fractal-trusted-multiyear
task/strategy-autopsy-report
task/sync-claude-md-with-roadmap
```

### Suggested cleanup command

```bash
# Run from the repo root. -d (lowercase) refuses to delete unmerged branches,
# so this is safe — git will block any branch that isn't fully merged.
git branch -d \
  review/frontend-cleanup \
  review/frontend-import \
  task/add-roadmap \
  task/backend-read-api \
  task/backtest-csv-export \
  task/compare-r-histogram \
  task/config-snapshot-display \
  task/data-quality-candles \
  task/delete-backtest-runs \
  task/fractal-import-compat \
  task/frontend-backtests-compare \
  task/frontend-backtests-detail \
  task/frontend-backtests-filters \
  task/frontend-backtests-list \
  task/frontend-import-form \
  task/frontend-journal-notes \
  task/frontend-monitor-live \
  task/frontend-r-histogram \
  task/frontend-replay \
  task/frontend-strategies \
  task/frontend-types-migration \
  task/openapi-typegen \
  task/phase-2-closeout \
  task/prop-firm-simulator \
  task/real-command-center \
  task/rename-backtest-runs \
  task/run-tags \
  task/sample-fractal-trusted-multiyear \
  task/strategy-autopsy-report \
  task/sync-claude-md-with-roadmap
```

## Investigate before deleting — `review/frontend-monitor`

**Status:** 1 commit ahead of `main`, last touched 2026-04-23, but the branch state is wildly behind. `git diff main..review/frontend-monitor --stat` shows 94 files changed and ~12,500 lines DELETED — including `frontend/lib/api/generated.ts`, `shared/openapi.json`, and `scripts/generate-types.sh`.

**Translation:** this branch was created before the type-generation pipeline existed. The 1 unique commit is `061d3cf "Wire /monitor page to GET /api/monitor/live with 5s polling"` — and that work appears to already be on `main` via `task/frontend-monitor-live` (which IS merged). The branch was never rebased forward, so it now looks like a giant deletion if you diff it against current `main`.

**Recommendation:** confirm by checking the monitor page on `main` — if `/monitor` already polls live, the unique commit is duplicate work and the branch is safe to delete with `git branch -D review/frontend-monitor` (capital D since it's not technically merged via the merge graph). If you're not sure, leave it — disk cost is zero.

## Why I didn't delete anything

Per the autonomous-session boundaries documented in `SESSION_NOTES.md` and the plan file, branch deletion is a destructive op that needs your hands on the keyboard. `git branch -d` is the safe form (refuses to delete unmerged work), but you should still review the list before running it.
