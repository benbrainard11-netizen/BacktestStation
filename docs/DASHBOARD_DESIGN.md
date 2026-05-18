# Dashboard Design — 4-screen operator console

_Spec for the operator-facing dashboard. Implementation owner: 247 (frontend + backend API). Spec owner: benpc._

## Goal

Replace "remember which command to run" with "open the dashboard and see the state." Operator-grade tool for a single-user solo lab, not a multi-tenant analytics product.

## Tech stack

- **Frontend**: Existing `frontend/` Next.js + React + TypeScript app. Use generated types from `shared/openapi.json`. New routes added to current routing.
- **Backend**: FastAPI endpoints in `backend/app/api/dashboard/`. Read-only queries against `meta.sqlite` + R2 + local data.
- **Charts**: Recharts (already in project) or a similarly lightweight lib. No D3.
- **State**: SWR or react-query for data fetching. No Redux. Refresh-on-demand, not realtime.
- **Auth**: None (single-user localhost-only).

## Design principles

1. **Read-mostly.** Operator actions are explicit buttons that POST to specific endpoints. No accidental mutations.
2. **Pull, don't push.** Manual refresh + cron-style auto-refresh (e.g., every 60 sec). No websockets in v1.
3. **One screen, one question.** Each screen answers one operator question. No mega-dashboards.
4. **Empty states matter.** "No paper trade data yet — start one via `bs paper start`" is a real screen state.
5. **Plain tables beat pretty charts.** Operator wants to see specific values, not vibes.

## 4 Screens

### 1. Data Health (`/data-health`)

**Question answered**: "Can I trust the data right now?"

**Sections** (top to bottom):

#### R2 sync status
- Last `_research_inventory.json` generated_at
- Total objects + total GB in bucket
- Time since last publish
- Status: ✓ recent (<1 day) / ⚠ stale (1-7 days) / ✗ very stale (>7 days)

#### Local data coverage
- 1m bars: date range + symbol count
- TBBO: date range + symbol count
- MBP-1: date range + symbol count
- research_events: row count + feature count
- For each, latest_date + days_since_latest

#### Latest validation report
- Snapshot it ran against
- Pass / Warn / Fail counts
- Top 5 failing gates with partition counts
- Click-through to full report

#### Known gaps
- Pulled from `partition_validation_findings` where severity = fail
- Filterable by schema, symbol, date

**Backend endpoints**:
- `GET /api/dashboard/data-health/r2-status`
- `GET /api/dashboard/data-health/local-coverage`
- `GET /api/dashboard/data-health/latest-validation`
- `GET /api/dashboard/data-health/findings?severity=fail`

**Refresh cadence**: Manual + auto-refresh every 5 min.

#### Wireframe (ASCII)

```
+---------------------------------------------------------------+
| Data Health                              [⟳ refresh]          |
+---------------------------------------------------------------+
| R2 SYNC                                                       |
|   Last publish: 2026-05-17 22:30:00 UTC (1h 12m ago)  ✓      |
|   Objects: 314 | Size: 7.1 GB                                 |
+---------------------------------------------------------------+
| LOCAL COVERAGE                                                |
|   1m bars       | 2015-01-01 - 2026-05-15 | 28 symbols  ✓    |
|   TBBO          | 2025-05-01 - 2026-05-15 |  1 yr      ⚠    |
|   MBP-1         | 2026-03-02 - 2026-05-15 | 58 days     ⚠    |
|   research_events: 4.22M rows, 15 features          ✓        |
+---------------------------------------------------------------+
| LATEST VALIDATION (snapshot abc123...)                        |
|   Total: 4218  | Pass: 4180 | Warn: 35 | Fail: 3   ⚠         |
|   Top failing gates:                                          |
|     missing_minutes: 18 partitions                            |
|     sequence_monotonic: 7 partitions                          |
|   [View full report →]                                        |
+---------------------------------------------------------------+
| KNOWN GAPS (severity=fail)                                    |
| schema   symbol     date        gate             count        |
| ohlcv-1m NQ.c.0     2020-03-12  missing_minutes  73           |
| ohlcv-1m ES.c.0     2020-03-12  missing_minutes  68           |
| tbbo     NQ.c.0     2025-08-05  bid_le_ask       2            |
+---------------------------------------------------------------+
```

### 2. Trials (`/trials`)

**Question answered**: "What experiments are/were running?"

**Sections**:

#### Active hypotheses
List of `hypotheses` with status = `active`. Each shows:
- Title
- Status
- Owner / created_at
- Active trial group count
- Click-through to detail

#### Active trial groups
List of `trial_groups` with status = `draft` or `running`. Each shows:
- Name + linked hypothesis
- Selection rule
- Trial count (completed/total)
- Click-through to detail

#### Recent locks
List of `trial_lock_records` ordered by `locked_at` desc, last 10. Each shows:
- Lock type (pre_validation / pre_test / final)
- Linked trial group
- Code commit SHA + dataset_snapshot_id (linked)
- Status (active / completed / abandoned / superseded)

#### Trial group detail subpage (`/trials/<id>`)
- Full hypothesis text
- Search space JSON (rendered)
- All trials in the group (table)
- Selection rule + selected trial
- Lock chain visualization

**Backend endpoints**:
- `GET /api/dashboard/trials/hypotheses`
- `GET /api/dashboard/trials/groups`
- `GET /api/dashboard/trials/locks/recent`
- `GET /api/dashboard/trials/group/<id>`

### 3. Candidates (`/candidates`)

**Question answered**: "What strategies are at what stage?"

**Sections**:

#### Lifecycle status board
Columns for each `CANDIDATE_LIFECYCLE` state (draft / research_only / needs_more_validation / paper_ready / micro_live / scale_candidate / killed / archived). Cards per candidate within each column. Each card shows:
- Strategy name + version
- Last status transition date
- Linked promotion packet (if any)
- Quick action: "View details" / "Promote" / "Kill"

#### Per-candidate detail page (`/candidates/<id>`)
- Full lifecycle history (state transitions)
- Linked trials + trial groups
- Backtest runs against this candidate
- Promotion packet (memo if exists)
- Action buttons: promote / demote / kill (with required-gate validation)

**Backend endpoints**:
- `GET /api/dashboard/candidates/list`
- `GET /api/dashboard/candidates/<id>`
- `POST /api/dashboard/candidates/<id>/promote`
- `POST /api/dashboard/candidates/<id>/kill`

#### Wireframe

```
+---------------------------------------------------------------+
| Candidates                                                    |
+---------------------------------------------------------------+
| DRAFT (0) | RESEARCH_ONLY (3) | NEEDS_VALIDATION (1) |       |
|           | • v8a OGAP        | • 2-family core      |       |
|           |   rejection       |   (OB+Sweep)         |       |
|           | • FVG strict (s)  |                      |       |
|           | • OB strict (s)   |                      |       |
+---------------------------------------------------------------+
| PAPER_READY (0) | MICRO_LIVE (0) | SCALE_CANDIDATE (0) |     |
+---------------------------------------------------------------+
| KILLED (2)                                                    |
| • 4-family Type B (v20 partial fail, 2026-05-17)              |
| • Swing reversed (regime artifact, 2026-05-17)                |
+---------------------------------------------------------------+
```

### 4. Live Monitor (`/live-monitor`)

**Question answered**: "How is paper / live trading going right now?"

**Sections** (when paper trade is active):
- Today's expected vs realized signals
- Drift report: realized R vs backtest expected R
- Recent fills + missed signals
- Active positions
- Daily/weekly P&L

**Empty state** (paper trade not started):
- Clear message: "No paper trade active. Start one via `bs paper start <candidate_id>`."
- Link to CANDIDATE_LIFECYCLE.md for "what does paper_ready mean?"

**Backend endpoints**:
- `GET /api/dashboard/live/active-candidates`
- `GET /api/dashboard/live/signals?since=...`
- `GET /api/dashboard/live/drift-report`
- `GET /api/dashboard/live/positions`

**Note**: This screen is mostly a stub in v1 since paper trade hasn't started. Build the empty state + the data structures. Real charts come in week 3.

## Routing + global navigation

```
/                       → redirect to /data-health
/data-health            → Data Health screen
/trials                 → Trials list
/trials/<id>            → Trial group detail
/candidates             → Candidates board
/candidates/<id>        → Candidate detail
/live-monitor           → Live Monitor

Sidebar nav: 4 items + a "Refresh All" button.
Header: project name + current branch (read from git) + last refresh time.
```

## Implementation phases

### Week 1: Data Health (~3 days for 247)
- Backend endpoints (1 day)
- Frontend page + tables (1.5 days)
- Polish + tests (0.5 day)

### Week 2: Trials + Candidates (~3 days)
- Backend endpoints for trials (0.5 day)
- Trials list + detail pages (1 day)
- Backend endpoints for candidates (0.5 day)
- Candidates board (1 day)

### Week 3: Live Monitor + polish (~3 days)
- Live Monitor empty state + structure (0.5 day)
- Endpoints for live data (1 day)
- Drift report logic + charts (1 day)
- Overall polish + cross-cutting fixes (0.5 day)

## Out of scope (v1)

- Mobile responsive (desktop only)
- Real-time updates (websockets) — pull-based only
- Multi-user auth — single-operator localhost
- Bulk operations / batch promotions
- Sharing / export (PDF reports, etc.)
- Notifications / alerts
- Theme customization
- Internationalization
- Embedded chat / AI prompts inside the dashboard
- Replacing the existing trade replay UI
- Public external exposure

## Data quality requirements before dashboard makes sense

For the dashboard to show useful data, the following must be populated:

| Table | Status |
|---|---|
| `dataset_snapshots` | 247 building now |
| `partition_validation_reports` | Phase 2 deliverable |
| `hypotheses` + `trial_groups` + `trials` | Tables exist; need backfill of historical work |
| `trial_lock_records` | v20 lock exists in YAML; needs DB row |
| `strategy_versions.status` | Needs candidates classified per CANDIDATE_LIFECYCLE |
| `backtest_runs` | Largely empty; needs going-forward population |

Some screens will show empty states until these tables are populated. That's expected for v1.

## Risks

| Risk | Mitigation |
|---|---|
| Scope creep | Screen-by-screen ship; don't start screen N+1 until screen N is done |
| API churn | Generate types from openapi.json per CLAUDE.md rule #4; commit changes together |
| Frontend complexity bloat | One library per concern; no Redux; SWR for fetching only |
| Empty data | Backfill scripts as needed; clear empty states in UI |
| 247 burnout | 3-week pace, not 1; check in weekly |

## Success criteria

End state at 2-3 weeks:

- Operator opens `/data-health` and sees current R2 + local + validation state in <2 sec
- Operator opens `/trials` and sees the v20 + future locked walk-forwards
- Operator opens `/candidates` and sees the lifecycle board with OB+Sweep, FVG, OGAP, killed candidates
- Operator opens `/live-monitor` and either sees paper trade or sees a clear empty-state CTA
- All 4 screens have manual + auto-refresh, work offline, no console errors

## What this dashboard is NOT

This dashboard is **not**:
- A trading terminal (no order entry, no live charts of price)
- A research IDE (no notebook integration, no code editor)
- A reporting tool for external stakeholders (single-operator use)
- A replacement for `meta.sqlite` queries (it surfaces a curated subset, not full DB access)
- A real-time monitoring system (pull-based, not push)

It's an operator console for "what's the state of the project right now."
