# Execution Plan — CLI + Validation + Dashboard

_2026-05-17. Plan to ship the three remaining foundation pieces flagged by 5.5 Pro Research. Two machines (benpc + ben-247) executing in parallel._

## Scope summary

| Item | Single-PC effort | Two-PC effort | Status |
|---|---|---|---|
| CLI consolidation (`bs ...` command surface) | 2-3 days | ~1.5 days | Not started |
| Full semantic data validation | 2-3 days | ~1.5 days | Inventory done; validation gates pending |
| Dashboard (4 screens) | 2-3 weeks | ~1.5-2 weeks | Not started |

**Total parallel timeline: 2-3 weeks** for everything.

## Division of labor

Per `branch_layout.md`: **benpc = compute/data lane, 247 = code/schema/DB lane.** Honored throughout this plan. Where dashboards need both, the work is explicitly split.

| Work | Owner | Why |
|---|---|---|
| Validation logic per schema | benpc | Knows the data, has read access to all parquets |
| `partition_validation_reports` schema | 247 | DB structure work |
| CLI Python implementation | 247 | Code work, lives in `backend/scripts/` |
| FastAPI endpoints (data health, trials, candidates) | 247 | Backend code, lives in `backend/app/api/` |
| Frontend pages (Next.js/React) | 247 | Existing `frontend/` infrastructure is theirs |
| Dashboard design specs | benpc | Drafting now while session is hot |
| Test data for dashboard development | benpc | Provides realistic snapshots from real research data |

## Phase 1 — Specs (TONIGHT, benpc, ~2 hr)

Write three design docs that the rest of the work executes against. Specs first means parallel work doesn't drift.

### Deliverable 1A: `docs/CLI_DESIGN.md`

Contents:
- Full command surface: every `bs <verb> <object>` we want to ship
- Subcommands grouped by domain (data, snapshot, trial, candidate, paper, doctor)
- File structure: where each subcommand's code lives
- Argument conventions, output formats (text default + `--json` flag)
- Implementation order (which 5 commands ship in v1, which wait for v2)

### Deliverable 1B: `docs/VALIDATION_DESIGN.md`

Contents:
- Semantic gates per schema (1m bars, tbbo, mbp-1, research_events)
- Gate severity (warn / fail)
- Output report structure: `partition_validation_reports` table fields
- Threshold defaults
- Integration with `bs data validate` CLI subcommand
- Integration with `dataset_snapshots.validation_report_id`

### Deliverable 1C: `docs/DASHBOARD_DESIGN.md`

Contents:
- 4 screens with wireframes (ASCII or screenshots): Data Health / Trials / Candidates / Live Monitor
- For each screen: data sources, query shapes, refresh cadence, primary actions
- API endpoint surface needed (so 247 can build endpoints in parallel with frontend)
- Phasing: which screens ship in week 1, week 2, week 3
- Defer-list: things explicitly NOT in v1 (real-time websockets, complex charting, mobile responsive, etc.)

## Phase 2 — Validation (~1.5 days parallel)

### Phase 2a (benpc, ~1 day)

Build the validation library:

```
backend/app/research/validation/
    __init__.py
    schema_gates.py        # generic gate runners
    gates_ohlcv.py         # OHLC invariant + gap detection + volume sanity
    gates_tbbo.py          # bid<=ask, sequence monotonic, valid action codes
    gates_mbp1.py          # similar to tbbo + depth fields
    gates_research_events.py  # event payload sanity
    runner.py              # walks a snapshot, runs all gates, produces a report
```

Then the partition-validation report module:

```
backend/scripts/data/validate_snapshot.py
```

Takes a `snapshot_id`, walks its partitions, runs the appropriate gates per schema, writes a `partition_validation_reports` row + per-partition findings.

### Phase 2b (247, ~0.5 day, parallel with 2a)

Build the `partition_validation_reports` schema + migration + tests. Schema sketch:

```sql
CREATE TABLE partition_validation_reports (
    id INTEGER PRIMARY KEY,
    snapshot_id VARCHAR(64) NOT NULL,            -- soft FK to dataset_snapshots
    generated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    generator_version VARCHAR(40),
    total_partitions INTEGER NOT NULL,
    partitions_pass INTEGER NOT NULL,
    partitions_warn INTEGER NOT NULL,
    partitions_fail INTEGER NOT NULL,
    summary_json TEXT,                            -- top-line metrics
    status VARCHAR(20) NOT NULL DEFAULT 'completed',
    notes TEXT
);
CREATE INDEX idx_pvr_snapshot ON partition_validation_reports(snapshot_id);

CREATE TABLE partition_validation_findings (
    id INTEGER PRIMARY KEY,
    report_id INTEGER NOT NULL REFERENCES partition_validation_reports(id),
    partition_r2_key VARCHAR(400) NOT NULL,
    schema VARCHAR(40) NOT NULL,
    symbol VARCHAR(20),
    date VARCHAR(10),
    gate_name VARCHAR(60) NOT NULL,
    severity VARCHAR(10) NOT NULL,                -- pass / warn / fail
    message TEXT,
    details_json TEXT
);
CREATE INDEX idx_pvf_report ON partition_validation_findings(report_id);
CREATE INDEX idx_pvf_severity ON partition_validation_findings(severity);
```

Then update `dataset_snapshots.validation_report_id` to FK against this (if we decide to enforce; soft coupling fine for v1).

## Phase 3 — CLI (~1.5 days parallel)

### Phase 3a (247, ~1 day)

Build CLI as a Typer or Click-based Python app entry point:

```
backend/scripts/cli/
    __init__.py
    main.py                # entrypoint; `bs` dispatches
    cmd_doctor.py          # health check (data, DB, R2 reachability)
    cmd_data.py            # bs data validate / bs data inventory
    cmd_snapshot.py        # bs snapshot create / list / show
    cmd_trial.py           # bs trial create / list / lock / run
    cmd_candidate.py       # bs candidate list / status / promote
    cmd_paper.py           # bs paper start / report (placeholder for now)
    cmd_status.py          # bs status (overall project snapshot)
```

Register `bs` as a console script via `pyproject.toml`.

Subcommands wire to existing functions where possible. Don't reinvent — wrap.

### Phase 3b (benpc, ~0.5 day, parallel with 3a)

- Write CLI tests (`backend/tests/test_cli.py`)
- Update `docs/CLI_DESIGN.md` with usage examples discovered during impl
- Update `docs/SYSTEM_MAP.md` to list the new CLI as core

## Phase 4 — Dashboard (~1.5-2 weeks parallel)

Big project. Decomposed into weekly milestones.

### Week 1: Data Health screen

#### Phase 4a (247, ~3 days)
- FastAPI endpoints:
  - `GET /api/dashboard/data-health/summary`
  - `GET /api/dashboard/data-health/partitions`
  - `GET /api/dashboard/data-health/validation-reports`
- Frontend page:
  - `/data-health` route
  - Tables for partition coverage, validation status, R2 sync status
  - Refresh on demand, no websockets

#### Phase 4b (benpc, parallel)
- Provide realistic snapshot + validation report data so 247 can test against real shapes
- Test the dashboard locally against real data

### Week 2: Trials + Candidates screens

#### Phase 4c (247, ~3 days)
- Endpoints:
  - `GET /api/dashboard/trials/list`
  - `GET /api/dashboard/trials/<trial_group_id>`
  - `GET /api/dashboard/candidates/list`
  - `GET /api/dashboard/candidates/<candidate_id>`
- Frontend pages:
  - `/trials` — lists hypotheses + trial groups + locks
  - `/candidates` — lists strategy versions by lifecycle status

#### Phase 4d (benpc, parallel)
- Backfill the trial registry with v8a/v13/v19/v20 work as historical trials (no lock records — exploratory only)
- Provide candidate-lifecycle test data

### Week 3: Live Monitor screen + polish

#### Phase 4e (247, ~3 days)
- Endpoints:
  - `GET /api/dashboard/live/signals`
  - `GET /api/dashboard/live/drift-report`
  - `GET /api/dashboard/live/missed-signals`
- Frontend page:
  - `/live-monitor` — depends on paper trade data existing
- If no paper trade data yet (likely), screen shows "No live data — paper trade not started" state

#### Phase 4f (benpc, parallel)
- Drive paper trade per `v21` lockfile in parallel
- Produce drift reports as data emerges
- Update SYSTEM_MAP with all the new code

## Coordination protocol

**Weekly check-in:** Sunday evening (e.g. 7pm). Each side reports:
- What shipped this week
- What's blocked
- What's queued for next week

**Daily handoff (if needed):** when one side's work feeds the other (e.g., 247 ships an API endpoint that benpc needs to test), the producing side commits + pushes + messages "ready for X."

**Branch hygiene:** each major piece on its own branch. Cherry-pick or merge into `assets/expanded-universe-v1` after review.

**Freeze list status:** the v20 lock is completed. The current freeze list (v8a simulator + 4 family definitions + slippage/cap/hour-filter) is effectively expired. New locked walk-forward (v21) will define its own freeze when written.

## Parallel work currently in flight

- **247**: building `dataset_snapshots` schema on `dataset-snapshots-v1` branch (per yesterday's prompt)
- **benpc**: foundation pass v3 just shipped; tonight's specs are next

These should both complete in the next ~24 hours, after which Phase 2-4 can begin in earnest.

## Deferred from this plan

Explicitly NOT in this execution plan:

1. **Live/Paper Monitor as a real-time view** (websockets, sub-second updates) — defer to phase 5 if needed
2. **Mobile-responsive dashboard** — desktop-first; mobile is later
3. **Multi-user auth on the dashboard** — single-operator for now
4. **Notifications / alerts** — pull-based dashboard only
5. **Replacing the existing trade replay UI** — different scope
6. **Public/external dashboard exposure** — internal use only
7. **Reconciling `experiments` table with `trial_groups` retroactively** — both exist; new work uses new tables

## Risk register

| Risk | Mitigation |
|---|---|
| Dashboard scope creep | Strict screen-by-screen phasing; ship one before starting next |
| CLI design churn | Spec doc locked before implementation; spec edits = bug fixes only after impl begins |
| Validation false positives blocking research | Severity = warn for borderline cases; only HARD fail on schema-level invariants |
| 247 + benpc divergence on schema | Both touch DB via shared models.py; review before merge |
| User burnout | Plan respects "2-3 week" pace, not "ship everything next week" |

## Success criteria

End state in 2-3 weeks:

- ✓ `bs doctor` runs and reports project health in <5 sec
- ✓ `bs snapshot create` and `bs data validate` work end-to-end
- ✓ `partition_validation_reports` table has real rows for at least one snapshot
- ✓ Dashboard's Data Health screen shows real R2 + local partition status
- ✓ Dashboard's Trials screen shows the v8a/v13/v20 historical work
- ✓ Dashboard's Candidates screen shows the 2-family core + others with their lifecycle states
- ✓ Live Monitor screen shows paper-trade data if available; otherwise "not started" state
- ✓ All new docs current per SYSTEM_MAP

## What to do next (tonight)

1. **benpc (me)**: write the three design docs — CLI_DESIGN, VALIDATION_DESIGN, DASHBOARD_DESIGN
2. **247**: keep shipping `dataset_snapshots` schema; nothing in this plan blocks on them tonight
3. **Commit + push everything** so both sides have full visibility
4. **Sleep**, start Phase 2/3 tomorrow with fresh head

The design docs are the gate. Without them, the parallel work drifts. With them, both sides can execute against a fixed target.
