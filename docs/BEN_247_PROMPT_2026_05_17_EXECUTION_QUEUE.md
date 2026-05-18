# 247 — Execution queue (CLI + validation tables + dashboard)

_From benpc, 2026-05-17. This is your sequential work queue. No timeline pressure — just execute in order. When one item lands cleanly, move to the next._

## Read first (all on `assets/expanded-universe-v1`)

1. `docs/EXECUTION_PLAN_2026_05_17.md` — the overall plan + division of labor
2. `docs/CLI_DESIGN.md` — full `bs` command surface spec
3. `docs/VALIDATION_DESIGN.md` — semantic gates + report tables
4. `docs/DASHBOARD_DESIGN.md` — 4 screens + API surface
5. `docs/SYSTEM_MAP.md` — what's where, what's status what
6. `docs/OPERATING_RULES.md` — the 5 non-negotiables
7. `docs/CANDIDATE_LIFECYCLE.md` — the state machine the dashboard surfaces
8. `docs/TABLE_REGISTRY.md` — every DB table classified

Total reading: ~20 minutes. Do it before writing anything.

## Lane split (re-confirm)

Per `branch_layout.md`:
- **benpc**: compute / data / validation logic / R2 publishing
- **247 (you)**: schema / DB / CLI / API endpoints / frontend

Everything below is your lane.

## The queue — execute sequentially

### Q1 — Finish `dataset_snapshots` schema

Already in flight on `dataset-snapshots-v1` per the prompt I sent earlier (`docs/BEN_247_PROMPT_2026_05_17_DATASET_SNAPSHOTS.md`). Land it, merge into `assets/expanded-universe-v1`, and post-merge: update `docs/SYSTEM_MAP.md` to mark the schema **core** instead of "247 building."

Acceptance: `dataset_snapshots`, `dataset_snapshot_partitions`, `dataset_snapshot_inputs` tables exist; migrations live in `_run_data_migrations`; at least one unit test creates and queries a snapshot.

### Q2 — Validation report schema

Per `docs/VALIDATION_DESIGN.md` "Output report shape" + `docs/EXECUTION_PLAN_2026_05_17.md` Phase 2b.

Add two tables:

```sql
CREATE TABLE partition_validation_reports (
    id INTEGER PRIMARY KEY,
    snapshot_id VARCHAR(64) NOT NULL,
    generated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    generator_version VARCHAR(40),
    total_partitions INTEGER NOT NULL,
    partitions_pass INTEGER NOT NULL,
    partitions_warn INTEGER NOT NULL,
    partitions_fail INTEGER NOT NULL,
    summary_json TEXT,
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
    severity VARCHAR(10) NOT NULL,
    message TEXT,
    details_json TEXT
);
CREATE INDEX idx_pvf_report ON partition_validation_findings(report_id);
CREATE INDEX idx_pvf_severity ON partition_validation_findings(severity);
```

Also add `dataset_snapshots.validation_report_id` (nullable FK soft coupling, no enforcement at DB level — informational).

Migration goes in `_run_data_migrations`. Tests in `backend/tests/test_validation_reports.py`. Update `docs/TABLE_REGISTRY.md` with the two new tables.

Acceptance: tables exist, migration is idempotent, test creates a report + 2 findings and queries them back.

### Q3 — CLI scaffold (`bs` command)

Per `docs/CLI_DESIGN.md`. v1 = 8 commands, exactly what's documented in that doc. Don't add v2 commands yet.

File layout:

```
backend/scripts/cli/
    __init__.py
    main.py
    cmd_doctor.py
    cmd_status.py
    cmd_data.py        # validate (calls validation runner once benpc lands it) + inventory (wrap scripts/data_inventory_report.py)
    cmd_snapshot.py    # create + list + show
    cmd_trial.py       # list only for v1
    output_format.py
```

Register `bs` as a console script in `pyproject.toml`. Add `typer` to deps if not already there.

Build order from the spec:
1. `main.py` skeleton + `cmd_doctor.py` first (proves the framework)
2. `cmd_status.py` (read-only, easy win)
3. `cmd_data.py inventory` (wraps existing `scripts/data_inventory_report.py`)
4. `cmd_snapshot.py` (wraps existing `backend/scripts/data/create_snapshot.py` + new list/show queries)
5. `cmd_trial.py list` (SELECT against `trial_groups`)
6. `cmd_data.py validate` — leave as a stub that prints "validation runner not landed yet" until benpc ships Phase 2a. Wire it up properly after.

Wrap, don't reinvent. If a Python function already exists, call it. The CLI is a thin shell.

Tests: `backend/tests/test_cli.py` using Typer's `CliRunner`. Per-command minimum: `--help` works, one happy path, one failure path.

Acceptance: `bs doctor` runs and reports green/red checks, `bs status` shows project snapshot, `bs snapshot list` returns at least one row after Q1, all tests green.

### Q4 — Dashboard week-1 backend (Data Health)

Per `docs/DASHBOARD_DESIGN.md` screen 1.

Endpoints in `backend/app/api/dashboard/`:
- `GET /api/dashboard/data-health/r2-status`
- `GET /api/dashboard/data-health/local-coverage`
- `GET /api/dashboard/data-health/latest-validation`
- `GET /api/dashboard/data-health/findings?severity=fail`

Read-only against `meta.sqlite` + R2 inventory JSON + local data dirs. No mutations.

After adding to `backend/app/schemas/`: run `bash scripts/generate-types.sh` per CLAUDE.md rule #4. Commit `shared/openapi.json` + `frontend/lib/api/generated.ts` together.

Tests: `backend/tests/test_dashboard_data_health.py`. Mock the R2 client and DB session; assert response shape.

### Q5 — Dashboard week-1 frontend (Data Health page)

Per `docs/DASHBOARD_DESIGN.md` screen 1 wireframe.

New route `/data-health` in `frontend/`. Use generated types from `shared/openapi.json` (not legacy `types.ts`). SWR for fetching. Plain tables, no charts on this screen. Manual refresh button + 5-min auto-refresh. Empty states for "no validation report yet" and "no findings."

Add to sidebar nav. Make `/` redirect to `/data-health`.

### Q6 — Dashboard week-2 backend (Trials + Candidates)

Per `docs/DASHBOARD_DESIGN.md` screens 2 + 3.

Endpoints:
- `GET /api/dashboard/trials/hypotheses`
- `GET /api/dashboard/trials/groups`
- `GET /api/dashboard/trials/locks/recent`
- `GET /api/dashboard/trials/group/<id>`
- `GET /api/dashboard/candidates/list`
- `GET /api/dashboard/candidates/<id>`
- `POST /api/dashboard/candidates/<id>/promote`  (defer body until lifecycle wiring lands; stub OK)
- `POST /api/dashboard/candidates/<id>/kill`     (same)

Regenerate types. Tests as before.

### Q7 — Dashboard week-2 frontend (Trials + Candidates pages)

Per `docs/DASHBOARD_DESIGN.md` screens 2 + 3.

`/trials`, `/trials/<id>`, `/candidates`, `/candidates/<id>`. Candidates board has columns per `CANDIDATE_LIFECYCLE` state per the wireframe.

### Q8 — Dashboard week-3 (Live Monitor)

Per `docs/DASHBOARD_DESIGN.md` screen 4. Mostly empty-state in v1 (paper trade hasn't started). Build the structure + endpoints + empty-state CTA. Real data flows in once benpc starts paper trade.

## Rules of engagement

- **Branch per major piece.** Q2 on its own branch, Q3 on its own, etc. Cherry-pick or merge into `assets/expanded-universe-v1` after review.
- **Commit + push when each Q lands.** Don't sit on big batches. benpc tests against your commits.
- **Update `docs/SYSTEM_MAP.md`** when something graduates from "247 building" to **core** / **active**.
- **CLAUDE.md rule #4 every time you touch schemas.** Regenerate types, commit them together.
- **CLAUDE.md rule #10.** 300-line file ceiling, 60-line function ceiling. Split aggressively.
- **No `--no-verify`.** Hooks run. If they fail, fix the underlying issue.
- **Spec is the gate.** If the spec docs disagree with what you're building, raise it before changing direction. Don't unilaterally rewrite the spec.

## Blockers from your side → benpc

If you hit any of these, drop a `BEN_BENPC_PROMPT_*.md` file and push:
- Spec ambiguity in any of the 3 design docs
- Need realistic test data for dashboard development
- Need validation runner to land before you can build `bs data validate` fully (expected after Q3)
- Pre-existing test failure in `test_liquidity_sweep_reactions.py::test_ob_confirmation_join` blocking CI

## What benpc is doing in parallel

- **Phase 2a (after Q2 lands)**: building `backend/app/research/validation/` library — `schema_gates.py`, `gates_ohlcv.py`, `gates_tbbo.py`, `gates_mbp1.py`, `gates_research_events.py`, `runner.py`, `validate_snapshot.py`. Writes to the tables you build in Q2.
- **Paper-trade prep**: 4 offline gates (roll-anomaly, day/week bootstrap, fill-model torture, single-account portfolio sim) on the surviving 2-family core (OB + Sweep) before paper trade starts.
- **Test data**: realistic snapshots + validation reports for dashboard development.

We're not blocking each other for now. Q1 → Q2 → Q3 should be your first focused stretch. Phase 2a starts on benpc side as soon as Q2 lands.

## Done condition (for the whole queue)

- All 4 dashboard screens render with real data
- `bs` CLI has 8 commands working
- `partition_validation_reports` has rows for at least one snapshot
- Empty states everywhere data isn't populated yet
- All new docs current per `docs/SYSTEM_MAP.md`

No timeline. Just sequential, clean handoffs.

— benpc
