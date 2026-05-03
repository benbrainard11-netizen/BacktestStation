# Hermes Operator Pack

Hermes is a small ops layer that helps Ben (and Husky) drive BacktestStation
without losing the plot. It is **not** an app feature, **not** an autonomous
agent, and **not** a runtime dependency. It is a set of plain-text rules,
prompt templates, and one read-only PowerShell script.

This document explains what Hermes is for, what it must never do, and how Ben
uses it day to day.

---

## What Hermes is for

1. **Prompt builder.** Turn messy idea dumps into strict, copy-pasteable
   prompts for Claude Code or Codex CLI.
2. **Repo reviewer.** Read a diff or branch and produce a structured review
   focused on bugs, data-integrity risks, and scope creep.
3. **Data integrity reviewer.** Inspect data-health, monitor, knowledge, and
   coverage signals to decide whether the warehouse can be trusted for a
   backtest.
4. **Daily status collaborator.** Run the snapshot script, then walk through
   the morning report with Ben.

That's the whole job. Nothing else.

## What Hermes must NOT do

- **No trading.** Hermes never places orders, never starts the live bot,
  never edits live config.
- **No SQLite mutation.** Hermes never writes to `data/meta.sqlite` directly.
  All schema and data changes go through the backend code path.
- **No warehouse deletion.** `D:\data\` is append-only. Hermes never deletes
  parquet, never rewrites raw DBN, never moves files.
- **No paid pulls without approval.** Databento historical pulls cost money.
  Hermes proposes a cost estimate and waits for Ben's explicit yes before any
  paid request is run.
- **No auto-merge.** Hermes can review and recommend. Ben decides what gets
  merged.

If a request to Hermes would violate any of these, Hermes refuses and asks
Ben to confirm — even if Ben asked for it. The rules above beat the prompt.

---

## How to run the status snapshot

The snapshot is one read-only PowerShell script. It prints a compact summary
of repo state, backend health, and recent logs. It never modifies anything.

From the repo root in PowerShell:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\hermes_status_snapshot.ps1
```

Or, if execution policy is already permissive:

```powershell
.\scripts\hermes_status_snapshot.ps1
```

The script will:

1. Print the current timestamp.
2. Print the current git branch and the latest commit.
3. Print `git status --short` so you see anything dirty.
4. Try to hit local backend endpoints if `uvicorn` is running on port 8000:
   - `/api/health`
   - `/api/data-health`
   - `/api/monitor/live`
   - `/api/knowledge/health`
   - `/api/datasets/coverage`
5. If the backend is not running, it prints `BACKEND OFFLINE` for those
   sections and keeps going. It never starts the server for you.
6. Print the tail of `data/live_inbox/import.log` if it exists.

Pipe to a file if you want to paste the whole snapshot into a chat:

```powershell
.\scripts\hermes_status_snapshot.ps1 | Out-File -Encoding utf8 hermes_snapshot.txt
```

---

## How to use each skill

The three skills live under `.hermes/skills/`. Each one is a Markdown file
that Ben opens, fills in, and feeds to Claude Code, Codex CLI, or another
chat. Hermes itself does not need to be installed — the skills are templates
any model can follow.

### `prompt-builder.md`

Use when Ben has an idea but it is half-formed. Paste the messy idea into the
template and the output is a strict prompt with goal, scope, non-goals,
acceptance criteria, tests, and rollback notes.

When to reach for it: any time you are about to ask Claude/Codex to do
something more than a one-line fix.

### `repo-reviewer.md`

Use after Claude or Codex has shipped a chunk of changes — staged, on a
branch, or in a PR. Run `git diff` (or `gh pr diff <n>`) and feed the diff
into the template. Output: bugs, data-integrity risks, overbuilt parts,
missing tests, and a recommended next action.

When to reach for it: before merging anything Claude or Codex wrote.

### `data-integrity-reviewer.md`

Use before running a backtest you intend to act on, or after a data pull,
ingester restart, or scheduled-task change. Run the snapshot script, paste
the output plus any log tails, and the reviewer returns a verdict:
trustworthy / suspicious / broken, with a fix-priority list.

When to reach for it: any time data freshness or coverage actually matters.

---

## Worked examples

### Example 1: messy idea turned into a strict prompt

**Ben's input (messy):**

> the trade replay page is slow when there's a ton of trades and i want it to
> page or window or something also can we add a little badge that shows how
> many trades the run has

**Hermes runs `prompt-builder.md` and returns:**

```
Goal
Make /trade-replay/<id> usable for runs with thousands of trades by paginating
or windowing the trades list, and add a count badge to the run header.

Scope
- Only the /trade-replay/[id] page in frontend.
- Only the trades-list rendering and one header badge.

Non-goals
- No backend pagination changes; existing /api/backtests/{id}/trades stays.
- No replay-engine changes.
- No new endpoints.

Relevant context to inspect
- frontend/app/trade-replay/[id]/page.tsx
- frontend/components/replay/* (whatever renders the list)
- backend/app/api/backtests.py (just to confirm the trades endpoint shape)

Implementation requirements
- Render at most 200 trades per page; default to first page on load.
- Header badge: "<N> trades" using the existing length of the trades array.
- Use existing typography/components; no new design tokens.

Acceptance criteria
- A run with 5000 trades opens in under 1s on the local app.
- Paging controls are keyboard accessible.
- Type-check clean: npx tsc --noEmit.

Tests / validation
- Manually open a 5000-trade run and confirm responsiveness.
- Open a 50-trade run and confirm pagination still renders without errors.

Rollback notes
- One-file change in the replay page; revert by reverting that commit.
- No DB or schema changes. No API contract changes.
```

Ben pastes that into Claude Code or Codex CLI and the work starts on rails.

### Example 2: Claude shipped changes, Hermes reviews

**Ben:**

> claude just finished a branch that adds a /api/datasets/refresh endpoint.
> here's the diff. review it.

Ben copies `git diff main...HEAD` into the `repo-reviewer.md` template.
Hermes returns sections like:

```
Summary of changes
Adds POST /api/datasets/refresh that re-scans D:\data and updates the
datasets table. Touches backend/app/api/datasets.py, services/dataset_scan.py,
and one test file.

Bugs / correctness risks
- New endpoint is not gated; can be triggered by any local caller, fine
  locally but worth a TODO if Tier 2 ever exposes it.
- service writes to dataset_meta inside a single transaction; fine for now.

Data integrity risks
- Scan reads parquet headers only — does not mutate raw/. Good.
- Does not touch SQLite outside the dataset_meta table. Good.

Scope creep / overbuilt parts
- Adds a new "rescan_history" table that is not used anywhere. Recommend
  dropping until a second caller exists.

Missing tests
- No test covers the empty-warehouse case.
- No test covers a parquet file with a corrupt header.

Recommended next action
Drop the unused rescan_history table, add the two missing tests, then merge.
```

Ben tells Claude exactly what to fix, gets a clean second pass, then merges.

### Example 3: morning status report

08:30 ET, before market open. Ben opens PowerShell:

```powershell
.\scripts\hermes_status_snapshot.ps1 | Out-File -Encoding utf8 morning.txt
```

Ben pastes `morning.txt` into a chat with Hermes and runs the
`data-integrity-reviewer.md` skill. The output is:

```
Trustworthy
- Live ingester heartbeat is < 60s old.
- Knowledge health: 0 stale cards.

Suspicious
- /api/datasets/coverage shows ESH26 coverage gap on 2026-04-29; the
  preceding day looks complete.

Broken
- None.

Backtest risk
Medium. Any backtest that touches 2026-04-29 ESH26 will see a gap. Avoid
or backfill before relying on results from that window.

Fix priority
1. Confirm whether the 2026-04-29 gap is real (no trades) or a missed pull.
2. If a missed pull, schedule a backfill (paid; needs Ben approval).
3. If real, mark the day as a known low-volume holiday in the dataset
   notes and move on.
```

Ben now knows exactly what to look at before opening the dashboard.

---

## Files in this pack

```
docs/HERMES_OPERATOR.md              <-- this file
.hermes/MISSION.md                   <-- Hermes mission + rules
.hermes/skills/prompt-builder.md
.hermes/skills/repo-reviewer.md
.hermes/skills/data-integrity-reviewer.md
scripts/hermes_status_snapshot.ps1   <-- read-only snapshot
```

When Hermes is later wired in (locally, by Ben), it reads `MISSION.md` and
the three skills as prompts. Until then, Ben (or Husky) can use the same
files manually with any chat model.
