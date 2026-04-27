# BacktestStation

A local-first research and command center for personal futures trading. Imported + engine-generated backtest runs, per-trade replay (1m and tick-level), live monitoring, drift detection, retroactive risk-profile evaluation, and a futures data warehouse — all running on local hardware.

**Status (2026-04-27):** Phase 1 (Imported Results Command Center) shipped. Backtest engine, live ingester, and live-trades pipeline online. Trade replay shipped. 444 backend tests green. See [`docs/PROJECT_STATE.md`](docs/PROJECT_STATE.md) for the full live-state mirror.

## Where to look next

- **What we're building** → [`docs/ROADMAP.md`](docs/ROADMAP.md) — vision, current focus tier, deferred work, direction discipline rules.
- **What's running today** → [`docs/PROJECT_STATE.md`](docs/PROJECT_STATE.md) — the canonical snapshot, refreshed after each milestone.
- **Engineering rules** → [`CLAUDE.md`](CLAUDE.md) — non-negotiable rules for engine purity, schema discipline, mocked-page tagging, etc.
- **Machine roles + data ownership** → [`docs/LOCAL_INFRASTRUCTURE.md`](docs/LOCAL_INFRASTRUCTURE.md) — three-machine setup (server / dev / contributor), append-only data rules, Husky onboarding.
- **System design (current + future)** → [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — sections 0-3 are current; sections 4+ describe a long-term engine end-state.
- **Pre-merge review** → invoke the [`merge-review`](.claude/agents/merge-review.md) subagent before merging a branch.

## Stack

- **Backend:** FastAPI (Python 3.12), SQLAlchemy + SQLite (`meta.sqlite`), pyarrow, Pandas
- **Engine:** pure Python, deterministic, lookahead-tested
- **Frontend:** Next.js + TypeScript + Tailwind, lightweight-charts (replay)
- **Desktop shell:** Tauri (spawns Next.js + uvicorn sidecar as one window)
- **Data:** Databento (live TBBO + monthly historical MBP-1) → DBN (raw) → Parquet (queryable, Hive-partitioned by symbol + date)
- **Network:** Tailscale connects ben-247 (server) ↔ benpc (dev) ↔ Husky's PC (contributor)

## Repo layout

```
backend/    FastAPI + engine + ingest pipelines + tests (444 tests green)
frontend/   Next.js app + Tauri shell
shared/     Generated OpenAPI schema (source of truth: backend Pydantic)
docs/       Architecture, roadmap, schema spec, runbooks
.claude/    Project agents (e.g. merge-review)
data/       Local repo data (meta.sqlite, live_inbox/) — gitignored
```

The on-disk warehouse lives at `D:\data\` (or `BS_DATA_ROOT`), separate from this repo. See [`docs/SCHEMA_SPEC.md`](docs/SCHEMA_SPEC.md) for the canonical layout.

## Getting started

### Quickest path (Windows, desktop app)

```cmd
start.bat
```

Spawns the Tauri desktop window, which spawns Next.js (port 3000) + uvicorn (port 8000) as children. First run takes 60-90s for cargo to compile the shell.

Prerequisites: backend venv + frontend node_modules. See per-component setup below if `start.bat` complains.

### Backend (manual)

macOS / Linux:

```bash
cd backend
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
uvicorn app.main:app --reload --port 8000
```

Windows (PowerShell):

```powershell
cd backend
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
uvicorn app.main:app --reload --port 8000
```

Health check: `curl http://localhost:8000/api/health` → `{"status":"ok","version":"0.1.0"}`.

Tests: `pytest -q` (target: 444 passed).

### Frontend (manual)

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:3000. Type-check: `npx tsc --noEmit`.

### Generated API types

Frontend imports TypeScript types generated from the FastAPI OpenAPI schema. Regenerate after any schema change:

```bash
bash scripts/generate-types.sh
```

Both `shared/openapi.json` and `frontend/lib/api/generated.ts` are committed.

Drift check (fails if `shared/openapi.json` is stale):

```bash
cd backend
.venv/Scripts/python.exe -m app.cli.export_openapi --check
```

Use generated types in new code:

```ts
import type { components } from "@/lib/api/generated";
type NoteRead = components["schemas"]["NoteRead"];
```

## For collaborators

1. Read [`docs/ROADMAP.md`](docs/ROADMAP.md) first — that's what we're building right now.
2. Read [`docs/LOCAL_INFRASTRUCTURE.md`](docs/LOCAL_INFRASTRUCTURE.md) for machine roles + data ownership rules. (Especially: raw data is append-only.)
3. Read [`CLAUDE.md`](CLAUDE.md) for engineering rules — they apply to humans + AI agents alike.
4. One feature per branch, one PR per branch. Small PRs.
5. If a file passes 300 lines, split it.
6. Before merging: invoke the `merge-review` subagent. It reads the rules above and flags scope drift / engineering violations.
