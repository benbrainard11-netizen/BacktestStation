# BacktestStation

A local-first research and command center for personal futures trading. Imported and engine-generated backtest runs, per-trade replay (1m and tick-level), live monitoring, drift detection, retroactive risk-profile evaluation, and a futures data warehouse, all running on local hardware.

For live status (what is shipped, what is in progress, what is broken) see [`docs/PROJECT_STATE.md`](docs/PROJECT_STATE.md). That is the canonical snapshot. This README is the entry point.

## Where to look next

- **What we're building** see [`docs/ROADMAP.md`](docs/ROADMAP.md). Vision, current focus tier, deferred work.
- **What's running today** see [`docs/PROJECT_STATE.md`](docs/PROJECT_STATE.md). Canonical snapshot, refreshed after each milestone.
- **Engineering rules** see [`CLAUDE.md`](CLAUDE.md). Non-negotiable rules for engine purity, schema discipline, mocked-page tagging, etc. Applies to humans and AI agents.
- **AI agent ground rules** see [`AGENTS.md`](AGENTS.md). How Claude / codex agents are expected to behave inside this repo.
- **Machine roles and data ownership** see [`docs/LOCAL_INFRASTRUCTURE.md`](docs/LOCAL_INFRASTRUCTURE.md). Three-machine setup (server, dev, contributor), append-only data rules.
- **System design (current and future)** see [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md). Sections 0 to 3 are current, sections 4+ describe a long-term engine end-state.
- **Schema spec** see [`docs/SCHEMA_SPEC.md`](docs/SCHEMA_SPEC.md). Canonical warehouse layout.
- **Pre-merge review** invoke the [`merge-review`](.claude/agents/merge-review.md) subagent before merging a branch.

## Stack

- **Backend:** FastAPI (Python 3.12), SQLAlchemy + SQLite (`meta.sqlite`), pyarrow, Pandas.
- **Engine:** pure Python, deterministic, lookahead-tested.
- **Frontend:** Next.js (App Router) + TypeScript + Tailwind, lightweight-charts for replay.
- **Desktop shell:** Tauri (spawns Next.js + uvicorn sidecar as one window).
- **Data:** Databento (live TBBO + monthly historical MBP-1) into DBN (raw) then Parquet (queryable, Hive-partitioned by symbol and date).
- **Cloud mirror:** Cloudflare R2. Validated parquet uploads, `bsdata` client reads R2-then-local-cache.
- **Network:** Tailscale connects ben-247 (server) to benpc (dev) to Husky's PC (contributor).

## Repo layout

### Root files

```
README.md             you are here, project entry point
AGENTS.md             ground rules for AI agents working in this repo
CLAUDE.md             engineering rules and non-negotiables loaded on every Claude session
SIMPLIFY_PLAN.md      historical simplification plan from May 2026, reference only
.env.example          documented list of env vars (BS_DATA_ROOT, R2 creds, Databento, etc.)
.gitignore            excludes /data/, /staging/, /exports/, .venv/, node_modules/, etc.
start.bat             Windows one-click, spawns Tauri shell with Next.js + uvicorn children
.claude/              project-scoped Claude agents and slash commands
```

### Application code

```
backend/                          FastAPI app + engine + ingest + research + tests
  app/
    main.py                       FastAPI entrypoint, CORS, route registration
    api/                          route handlers, one module per resource
                                    backtests, inbox, monitor, replay, research,
                                    risk_profiles, settings, strategies, etc.
    backtest/                     pure engine: bars in, BacktestResult out
                                    engine.py, broker.py, orders.py, metrics.py,
                                    runner.py, instruments.py, events.py
    strategies/                   composable/, fractal_amd/, examples/
    features/                     reusable signal building blocks
                                    SMT, FVG touch, sweep, orderblock engulf,
                                    volume profile, decisive close, vol regime
    research/                     detectors, outcomes, labeled-event builders,
                                    reference levels, macro taxonomy, sessions
    ingest/                       data pipelines
                                    Databento live, historical pull, parquet mirror,
                                    R2 upload/download, legacy importers,
                                    bulk free pull, cost estimator, warehouse sync
    data/                         schema, manifest, reader, storage abstraction
                                    (LocalStorage + R2Storage on one reader codepath)
    services/                     business logic
                                    importer, drift, monte_carlo, prop_firm,
                                    autopsy, dataset_scanner, live_monitor, etc.
    schemas/                      Pydantic models, source of truth for OpenAPI
    db/                           SQLAlchemy session, models, migrations for meta.sqlite
    cli/                          Click commands (export_openapi, etc.)
    core/                         paths.py and shared helpers
  tests/                          119 test files, target green per PROJECT_STATE.md
  scripts/                        backend-only helpers
  pyproject.toml                  Python deps and dev extras

frontend/                         Next.js 15 + TS + Tailwind + Tauri shell
  app/                            App Router routes
                                    /, /inbox, /backtests, /strategies, /monitor,
                                    /library, /replay, /research, /data-health,
                                    /risk-profiles, /settings
  components/                     UI building blocks
                                    layout/, ui/, replay/, strategies/, atoms, Icon
  lib/                            client helpers
                                    api/ (generated types + fetch wrappers),
                                    format, navigation, poll, streaming, utils
  src-tauri/                      Rust shell, spawns Next.js + uvicorn as one window
  e2e/                            Playwright tests
  public/                         static assets

shared/
  openapi.json                    generated from backend Pydantic, committed

client/
  bsdata/                         pip-installable parquet client
                                    R2-first reader for outside-the-repo consumption,
                                    mirrors app.data.reader signatures
```

### Operations and research

```
scripts/                          repo-level operational scripts (PS1 + sh)
  generate-types.sh               regenerate frontend/lib/api/generated.ts from openapi
  install_*.ps1                   Windows scheduled tasks: daily pull, dataset scan,
                                    reconcile, ingester service, taildrop
  setup_ingester.ps1              one-time live ingester setup on ben-247
  mirror_to_husky.ps1             push warehouse subset to contributor machine
  audit_collection_node.ps1       sanity-check a collection node
  extract_design_bundle.mjs       import Figma JSX exports into design_extract/
  import_live_trades.ps1          load live JSONL into the live-trades pipeline

strategy_lab/                     strategy export / import tooling
  publish_export_release.py       package an anchor matrix as a release
  download_export_release.py      pull a published release locally
  load_anchor_matrix.py           load a release into the runtime
  sync_export_to_github.py        sync export releases to github
  EXPORT_INDEX.json               registry of published releases

samples/
  fractal_trusted_multiyear/      reference data export used by tests + docs

docs/                             215 docs grouped by prefix
                                    ARCHITECTURE.md, ROADMAP.md, PROJECT_STATE.md,
                                    SCHEMA_SPEC.md, LOCAL_INFRASTRUCTURE.md,
                                    SERVER_DEPLOYMENT.md, RUNBOOK_*.md,
                                    ML_*.md (research findings),
                                    R2_*.md, AI_*.md, BACKTEST_ENGINE.md,
                                    FRONTEND_API_REFERENCE.md, WISHLIST.md
```

### Local data (gitignored)

```
data/
  meta.sqlite                     local catalog: runs, strategies, notes, monitors
  backtests/                      per-run JSON output
  processed/                      cached intermediates
  logs/                           dev server logs
  spawn.log                       Tauri child process log
```

The on-disk parquet warehouse lives at `D:\data\` (or `$BS_DATA_ROOT`), separate from this repo. See [`docs/SCHEMA_SPEC.md`](docs/SCHEMA_SPEC.md) for the canonical layout.

### Archives (read-only history)

```
_frontend_archive_2026_05_01/     pre-simplify frontend, kept for component reference
design_extract/                   imported design bundle (Figma JSX + assets)
```

## Branch policy

Active branches on origin:

- `main` canonical, what runs in dev and on ben-247
- `caseybranch` collaborator working branch
- `assets/expanded-universe-v1` in-flight, R2 freshness on data health dashboard
- `wip/strategy-builder-v1-button-fix` open builder UX fix

Everything else has been pruned (2026-05-27). Old experiment, lab, and Claude-generated branches were deleted from origin. Anything you need from a deleted branch is recoverable from GitHub's deleted-branch reflog for ~90 days.

One feature per branch, one PR per branch. Small PRs. If a file passes 300 lines, split it.

## Getting started

### Quickest path (Windows, desktop app)

```cmd
start.bat
```

Spawns the Tauri desktop window, which spawns Next.js (port 3000) and uvicorn (port 8000) as children. First run takes 60 to 90 seconds for cargo to compile the shell.

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

Health check:

```bash
curl http://localhost:8000/api/health
# {"status":"ok","version":"0.1.0"}
```

Tests:

```bash
pytest -q
```

Target: full green. Check `docs/PROJECT_STATE.md` for the current canonical test count.

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

1. Read [`docs/ROADMAP.md`](docs/ROADMAP.md) first. That is what we are building right now.
2. Read [`docs/LOCAL_INFRASTRUCTURE.md`](docs/LOCAL_INFRASTRUCTURE.md) for machine roles and data ownership rules. Especially: raw data is append-only.
3. Read [`CLAUDE.md`](CLAUDE.md) for engineering rules. They apply to humans and AI agents alike.
4. One feature per branch, one PR per branch. Small PRs.
5. If a file passes 300 lines, split it.
6. Before merging, invoke the `merge-review` subagent. It reads the rules above and flags scope drift and engineering violations.
