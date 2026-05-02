# BacktestStation — Frontend API Reference

Single-source API contract for the BacktestStation frontend rewrite. Every router, every endpoint, every payload field that the FastAPI backend (`backend/app/`) currently exposes — pulled directly from the Pydantic schemas, not paraphrased.

Verified against the code on 2026-04-29.

---

## 1. Quick start

### Run the backend

The repo ships a one-click launcher (`start.bat` at the repo root) that spawns Tauri, which spawns Next.js (port 3000) and the FastAPI sidecar. To run the backend on its own:

```bat
cd backend
.venv\Scripts\activate
uvicorn app.main:app --reload --port 8000
```

There is no `pyproject.toml [project.scripts]` entry, no `make dev`, no `Procfile`. The Tauri sidecar invocation in `frontend/src-tauri/...` runs `uvicorn app.main:app` on port 8000 by default.

### Base URL

`http://localhost:8000/api`

Every router declared in `backend/app/main.py` is mounted with the `/api` prefix. The `/api` segment is part of the URL — it is not implicit.

### Auth

None. No middleware, no header check, no cookie session. Local-first single-user app — endpoints are unauthenticated. Do not design login screens unless the user explicitly asks for one.

### CORS

`backend/app/main.py` allows exactly one origin: `http://localhost:3000`. Methods and headers are wide open. `allow_credentials=True`.

If the new frontend dev server runs on a different port, the backend's CORS config has to be widened first.

### OpenAPI / docs

FastAPI's defaults are not overridden, so the following are live:

- `GET /docs` — Swagger UI
- `GET /redoc` — ReDoc
- `GET /openapi.json` — machine-readable schema

The repo also commits a frozen copy at `shared/openapi.json` (regenerated via `scripts/generate-types.sh`).

### Backend version

`0.1.0` (`backend/app/__init__.py`). Surfaced via `GET /api/health` and `GET /api/settings/system`.

---

## 2. Domain model

A frontend-readable mental model of the nouns. Verified against schemas + services, not just docs.

### Strategy

A research artifact: a named hypothesis (e.g. "Fractal AMD") with a slug, a status in the lifecycle (`idea` → `research` → `building` → `backtest_validated` → `forward_test` → `live` → `retired` → `archived`), description markdown, and tags. A strategy holds zero or more **strategy versions**. Strategies are creatable and editable in the UI; deleting one is only allowed when it has zero versions (use archive instead).

### Strategy version

A specific snapshot of a strategy's rules: `entry_md`, `exit_md`, `risk_md`, optional `git_commit_sha`. Every backtest run is attached to exactly one strategy version. A version may be marked `archived_at`. A version may also designate a `baseline_run_id` — the run the Forward Drift Monitor compares live behavior against. Deletion of a version is refused with 409 if any runs are attached; archive instead.

### Backtest run

The result of running a strategy version against a dataset. Stored as a `BacktestRun` row plus three child collections in SQLite: `Trade`, `EquityPoint`, `RunMetrics`, and a `ConfigSnapshot`. Each run has:

- `source` ∈ `imported` | `engine` | `live` — where it came from
- `status` ∈ `succeeded` | `failed` | `running` (engine runs are synchronous today, so `running` is rarely seen; imported and live runs land already-complete)
- `name`, `symbol`, `timeframe`, `session_label`, `start_ts`, `end_ts`, `tags`, `import_source`

Imported runs come from CSV/JSON file uploads. Engine runs come from `POST /api/backtests/run` and execute synchronously in-process. Live runs are written by the live bot's daily JSONL drop and the import scheduled task on the user's PC.

There is no async queue or polling lifecycle today — the only long-ish call is `POST /api/backtests/run` which blocks until the engine finishes.

### Experiment

A structured research entry on the **Experiment Ledger**. Links a `strategy_version_id` to a `hypothesis` (required), an optional `baseline_run_id`, an optional `variant_run_id`, a freeform `change_description`, and a `decision` ∈ `pending` | `promote` | `reject` | `retest` | `forward_test` | `archive`. Used for "we changed X, did it work?" tracking. Both linked runs must belong to the same parent strategy as the experiment's version (validated server-side).

### Prop firm profile

An editable `FirmRuleProfile` row describing one prop-firm evaluation account: account size, profit target, max drawdown, daily loss limit, trailing drawdown, consistency rule, payout split, fees, etc. Profiles are seeded from a static `PRESETS` dict on first run, but every field is user-editable. A profile carries a verification stamp (`unverified` | `verified` | `demo`) — editing any rule field on a `verified` profile auto-flips it back to `unverified`. Profiles are referenced by `profile_id` (string slug like `"topstep_50k_combine"`), not numeric id.

A separate **prop-firm simulation** (`PropFirmSimulation` row) is one Monte Carlo run that uses one or more backtests as the trade pool, applies one firm profile, and records aggregated pass/fail/payout stats plus selected sample paths.

### Risk profile

A user-defined cap set applied retroactively to a backtest run: `max_daily_loss_r`, `max_drawdown_r`, `max_consecutive_losses`, `max_position_size`, optional `allowed_hours` whitelist, plus a free `strategy_params` dict that prefills the run-a-backtest form. All caps in R-multiples (contract-size-independent). A profile can be `evaluated` against a run; the response is a list of cap violations, no mutation.

### Replay (`/replay`)

Per-day chart playback: 1-minute bars for one symbol on one date, plus optional entry/exit markers from a backtest run that fired that day, plus auto-detected Fair Value Gap zones over the day's resampled 5-minute candles. Used to visually inspect "did this trade enter inside the gap zone?". No tick-level data here.

### Trade replay (`/trade-replay`)

A different feature, not a renamed `replay`. TBBO-tick-resolution playback windowed around one specific historical **live** trade (`BacktestRun(source="live")` only — engine and imported runs aren't surfaced). Picker lists live runs with their trades; each trade carries `tbbo_available` so rows whose date partition isn't on disk render disabled. The detail endpoint returns all TBBO ticks within `[entry - lead_seconds, exit + trail_seconds]`.

### Autopsy

Deterministic post-mortem of a backtest run. Pure rule-based — no LLM. Ingests the run + trades + metrics, produces an `overall_verdict`, `edge_confidence` 0-100, `go_live_recommendation` ∈ `not_ready` | `forward_test_only` | `small_size` | `validated`, and lists of strengths / weaknesses / overfitting warnings / risk notes / best+worst conditions slices.

### Monitor

The `/monitor` page's three concerns:

1. **Live status** — the running bot's last heartbeat written to a JSON file
2. **Ingester health** — the live tick ingester's heartbeat
3. **Live-trades pipeline** — the daily import scheduler, plus the latest live `BacktestRun` row, plus the inbox JSONL file presence

Plus session journal (`live_signals`) and Forward Drift comparisons against the version's baseline.

### Imports

CSV/JSON uploader for existing backtest result bundles produced outside the engine. Multipart form upload of `trades_file` + `equity_file` + optional `metrics_file` + optional `config_file`, with metadata fields. Synchronous — returns the new `backtest_id` immediately on success or 422 on validation failure.

### Datasets / Data Health

`Dataset` is one warehouse file: a parquet partition or DBN file that's been registered. The `datasets` table is a queryable cache that `POST /api/datasets/scan` reconciles against the on-disk warehouse rooted at `BS_DATA_ROOT` (default `C:/data` on Windows). `/data-health` aggregates the same data into a single page-friendly payload (warehouse summary by schema + scheduled-task health + free disk + last scan timestamp).

---

## 3. Endpoint catalog

### Health (`backend/app/api/health.py`)

#### GET /api/health

**Purpose:** Liveness check. Returns version + status string.
**Response 200 (`HealthResponse`):**

```
{ "status": "ok", "version": "0.1.0" }
```

**Errors:** none.

---

### Imports (`backend/app/api/imports.py`)

Router prefix: `/import` (singular).

#### POST /api/import/backtest

**Purpose:** Multipart upload of an existing backtest result bundle (trades + equity + optional metrics + optional config). Synchronous — the response carries the new `backtest_id`.
**Content-Type:** `multipart/form-data`
**Form fields:**

- `trades_file` (file, required) — CSV/JSON of trades
- `equity_file` (file, required) — CSV/JSON of equity points
- `metrics_file` (file, optional)
- `config_file` (file, optional)
- `strategy_name` (string, optional) — display name; if absent the importer infers
- `strategy_slug` (string, optional) — slug for the strategy; importer creates if missing
- `version` (string, optional) — version identifier
- `run_name` (string, optional) — human label for the run
- `symbol` (string, optional) — e.g. `"NQ"`, `"MNQ"`
- `timeframe` (string, optional) — e.g. `"1m"`
- `session_label` (string, optional) — e.g. `"RTH"`
- `import_source` (string, optional) — free text; e.g. `"vectorbt"`, `"live_jsonl"`
  **Response 201 (`ImportBacktestResponse`):**

```
{
  "backtest_id": int,
  "strategy_id": int,
  "strategy_version_id": int,
  "trades_imported": int,
  "equity_points_imported": int,
  "metrics_imported": bool,
  "config_imported": bool
}
```

**Errors:** 422 on parse / validation failure (invalid CSV, mismatched fields).

---

### Strategies (`backend/app/api/strategies.py`)

Two routers:

- `router` mounted at `/api/strategies`
- `versions_router` mounted at `/api/strategy-versions`

#### GET /api/strategies/stages

**Purpose:** Lifecycle vocabulary. Used to drive the pipeline-board column order.
**Response 200 (`StrategyStagesRead`):**

```
{ "stages": ["idea", "research", "building", "backtest_validated", "forward_test", "live", "retired", "archived"] }
```

#### GET /api/strategies

**Purpose:** List all strategies with their versions eagerly loaded (`selectinload`). Newest first.
**Response 200:** `list[StrategyRead]`
**`StrategyRead`:**

```
{
  "id": int,
  "name": str,
  "slug": str,                       # lowercase
  "description": str | null,
  "status": str,                     # one of STRATEGY_STAGES
  "tags": list[str] | null,
  "created_at": datetime,
  "versions": list[StrategyVersionRead]
}
```

**`StrategyVersionRead`:**

```
{
  "id": int,
  "strategy_id": int,
  "version": str,
  "entry_md": str | null,
  "exit_md": str | null,
  "risk_md": str | null,
  "git_commit_sha": str | null,
  "created_at": datetime,
  "archived_at": datetime | null,
  "baseline_run_id": int | null
}
```

#### POST /api/strategies

**Purpose:** Create a new strategy.
**Request body (`StrategyCreate`):**

```
{
  "name": str,                       # required, non-empty after trim
  "slug": str,                       # required, lowercased server-side, max 120
  "description": str | null,
  "status": str,                     # default "idea"; must be in STRATEGY_STAGES
  "tags": list[str] | null
}
```

Extra fields rejected (`extra="forbid"`).
**Response 201:** `StrategyRead` (with empty `versions: []`).
**Errors:** 409 if slug already exists. 422 on validation.

#### GET /api/strategies/{strategy_id}

**Purpose:** One strategy with versions. **Response:** `StrategyRead`. **Errors:** 404.

#### GET /api/strategies/{strategy_id}/runs

**Purpose:** All backtest runs across every version of the strategy. Replaces "fetch all runs and filter client-side". Newest first.
**Response 200:** `list[BacktestRunRead]`. **Errors:** 404 if strategy missing.

#### PATCH /api/strategies/{strategy_id}

**Purpose:** Partial update. Only fields actually present in the body are applied (uses `model_fields_set`).
**Request body (`StrategyUpdate`):** all fields optional; `name`, `description`, `status`, `tags`. Extra rejected.
**Response 200:** `StrategyRead`. **Errors:** 404, 422.

#### DELETE /api/strategies/{strategy_id}

**Purpose:** Hard delete — only allowed when the strategy has zero versions. To remove a strategy with imported data, archive it instead (`PATCH status="archived"`).
**Response:** 204 No Content.
**Errors:** 404 if not found. 409 if any versions still attached. Detail message includes the count.
**Side effects:** orphan strategy-level `Note` rows are deleted; nothing else is touched.

#### POST /api/strategies/{strategy_id}/versions

**Purpose:** Add a new version to a strategy.
**Request body (`StrategyVersionCreate`):**

```
{
  "version": str,                    # required, non-empty, max 40
  "entry_md": str | null,
  "exit_md": str | null,
  "risk_md": str | null,
  "git_commit_sha": str | null       # max 40
}
```

**Response 201:** `StrategyVersionRead`. **Errors:** 404 strategy, 409 duplicate version name within the strategy, 422.

#### PATCH /api/strategy-versions/{version_id}

**Purpose:** Edit a version's fields. Partial — only fields present are applied.
**Request body (`StrategyVersionUpdate`):** all optional: `version`, `entry_md`, `exit_md`, `risk_md`, `git_commit_sha`. `version` (if sent) must trim non-empty.
**Response 200:** `StrategyVersionRead`. **Errors:** 404, 422.

#### DELETE /api/strategy-versions/{version_id}

**Purpose:** Delete a version. Refused if any backtest runs are attached.
**Response:** 204. **Errors:** 404. 409 if runs attached (with the count and pointer to the archive flow).
**Side effects:** orphan version-level `Note` and `Experiment` rows are deleted.

#### PATCH /api/strategy-versions/{version_id}/archive

**Purpose:** Mark version archived. Sets `archived_at = now()` if not already set. Non-destructive.
**Response 200:** `StrategyVersionRead`. **Errors:** 404.

#### PATCH /api/strategy-versions/{version_id}/unarchive

**Purpose:** Clear `archived_at`. **Response 200:** `StrategyVersionRead`. **Errors:** 404.

#### PATCH /api/strategy-versions/{version_id}/baseline

**Purpose:** Set or clear the version's baseline run for the Forward Drift Monitor. The baseline is the run live behavior is compared against.
**Request body (`StrategyVersionBaselineUpdate`):**

```
{ "run_id": int | null }
```

`null` clears.
**Response 200:** `StrategyVersionRead`.
**Errors:** 404 version. 404 if `run_id` references a non-existent run. 422 if the run is `source="live"` (live cannot be its own baseline).

---

### Backtests (`backend/app/api/backtests.py`)

Router prefix: `/backtests`. Mixes engine kickoff with read endpoints.

#### GET /api/backtests/strategies

**Purpose:** Catalogue of strategies the engine resolver can run, with parameter schemas. The Run-a-Backtest form uses this to render typed inputs per strategy.
**Response 200:** `list[StrategyDefinitionRead]`
**`StrategyDefinitionRead`:**

```
{
  "name": str,                      # e.g. "fractal_amd" — passed back as RunRequest.strategy_name
  "label": str,                     # display name
  "description": str | null,
  "default_params": dict[str, any],
  "param_schema": {
    "type": "object",
    "properties": {
      "<param_name>": {
        "type": "number" | "integer" | "string" | "boolean",
        "label": str,
        "description": str | null,
        "min": float | int | null,
        "max": float | int | null,
        "step": float | int | null,
        "enum": list[any] | null
      },
      ...
    }
  }
}
```

Currently returns two definitions: `fractal_amd` (multi-instrument SMT/FVG strategy with 11 params) and `moving_average_crossover` (smoke-test, 4 params: `fast_period`, `slow_period`, `stop_ticks`, `target_ticks`). Hand-maintained list, not auto-discovered.

#### POST /api/backtests/run

**Purpose:** Synchronous engine backtest. Loads bars for `symbol`/`timeframe`/`start..end` from the warehouse, instantiates the strategy with `params`, runs the engine, writes outputs to disk, persists the new `BacktestRun` row, returns it.
**Request body (`BacktestRunRequest`):**

```
{
  "strategy_name": str,              # required, must match a name in /backtests/strategies
  "strategy_version_id": int,        # required, > 0; the version this run is attached to
  "symbol": str,                     # required, e.g. "NQ"
  "aux_symbols": list[str],          # default []; secondary instruments for multi-instr strategies
  "timeframe": str,                  # default "1m"
  "start": "YYYY-MM-DD",             # required, validated as ISO date
  "end": "YYYY-MM-DD",               # required; must be >= start
  "qty": int,                        # default 1, >= 1
  "initial_equity": float,           # default 25000.0, > 0
  "params": dict[str, any]           # default {}; strategy-specific
}
```

Extra fields rejected.
**Response 201:** `BacktestRunRead`.
**Errors:**

- 404 if `strategy_version_id` not found
- 422 if `strategy_name` is not in the engine resolver
- 422 if `load_bars` returns zero bars (warehouse missing data for the window)
- 422 on date validation (`start > end`)
  **Latency:** synchronous; can take seconds to minutes depending on date range. The frontend should disable the form during the call. There is no progress stream.

#### GET /api/backtests

**Purpose:** All backtest runs, newest first.
**Response 200:** `list[BacktestRunRead]`.
**`BacktestRunRead`:**

```
{
  "id": int,
  "strategy_version_id": int,
  "name": str | null,
  "symbol": str,
  "timeframe": str | null,
  "session_label": str | null,
  "start_ts": datetime | null,
  "end_ts": datetime | null,
  "import_source": str | null,
  "source": str,                    # "imported" | "engine" | "live"
  "status": str,                    # "succeeded" | "failed" | (rare) "running"
  "tags": list[str] | null,
  "created_at": datetime
}
```

#### GET /api/backtests/{backtest_id}

**Purpose:** One run.
**Response 200:** `BacktestRunRead`. **Errors:** 404.

#### GET /api/backtests/{backtest_id}/trades

**Purpose:** All trades for the run, ordered by `entry_ts ASC`.
**Response 200:** `list[TradeRead]`
**`TradeRead`:**

```
{
  "id": int,
  "backtest_run_id": int,
  "entry_ts": datetime,
  "exit_ts": datetime | null,
  "symbol": str,
  "side": str,                      # "long" | "short"
  "entry_price": float,
  "exit_price": float | null,
  "stop_price": float | null,
  "target_price": float | null,
  "size": float,
  "pnl": float | null,
  "r_multiple": float | null,
  "exit_reason": str | null,        # "stop" | "target" | "eod" | "manual" — strings, no enum
  "tags": list[str] | null
}
```

**Errors:** 404 if run missing.

#### GET /api/backtests/{backtest_id}/equity

**Purpose:** Equity curve points, ordered by ts ASC.
**Response 200:** `list[EquityPointRead]`

```
{ "id": int, "backtest_run_id": int, "ts": datetime, "equity": float, "drawdown": float | null }
```

**Errors:** 404.

#### GET /api/backtests/{backtest_id}/metrics

**Purpose:** Aggregated stats for the run.
**Response 200:** `RunMetricsRead`

```
{
  "id": int,
  "backtest_run_id": int,
  "net_pnl": float | null,
  "net_r": float | null,
  "win_rate": float | null,         # 0..1 fraction
  "profit_factor": float | null,
  "max_drawdown": float | null,     # dollars (sign convention: nonpositive)
  "avg_r": float | null,
  "avg_win": float | null,
  "avg_loss": float | null,
  "trade_count": int | null,
  "longest_losing_streak": int | null,
  "best_trade": float | null,
  "worst_trade": float | null
}
```

**Errors:** 404 if run or metrics missing (metrics may be missing on legacy imports).

#### GET /api/backtests/{backtest_id}/config

**Purpose:** Snapshot of the run's config (params, contract spec, etc.). The shape inside `payload` is freeform JSON — depends on what the importer or engine wrote.
**Response 200:** `ConfigSnapshotRead`

```
{ "id": int, "backtest_run_id": int, "payload": dict, "created_at": datetime }
```

**Errors:** 404.

#### PATCH /api/backtests/{backtest_id}

**Purpose:** Rename a run. Currently only `name` is editable.
**Request body (`BacktestRunUpdate`):**

```
{ "name": str | null }    # null clears the name; empty string after trim is rejected
```

**Response 200:** `BacktestRunRead`. **Errors:** 404, 422.

#### DELETE /api/backtests/{backtest_id}

**Purpose:** Cascade delete the run and all its children (trades, equity, metrics, config snapshot). Notes survive (nullable FK). Any `StrategyVersion.baseline_run_id`, `Experiment.baseline_run_id`, `Experiment.variant_run_id` pointing at this run are NULL'd before deletion.
**Response:** 204. **Errors:** 404.

#### PUT /api/backtests/{backtest_id}/tags

**Purpose:** Replace the full tag list. Empty list clears.
**Request body (`BacktestRunTagsUpdate`):**

```
{ "tags": list[str] }
```

Tags are trimmed and de-duped server-side.
**Response 200:** `BacktestRunRead`. **Errors:** 404.

---

### Backtest exports (`backend/app/api/backtest_export.py`)

Router prefix: `/backtests`. Read-only CSV streams, suffixed `.csv`. All return `Content-Type: text/csv` and `Content-Disposition: attachment; filename="backtest_{id}_{kind}.csv"`. An empty result returns an empty body, status 200.

#### GET /api/backtests/{backtest_id}/trades.csv

**Purpose:** All trades as CSV. Columns: `id, entry_ts, exit_ts, symbol, side, entry_price, exit_price, stop_price, target_price, size, pnl, r_multiple, exit_reason, tags`. `tags` is `;`-joined. Timestamps are `.isoformat()` strings or empty.
**Errors:** 404 if run missing.

#### GET /api/backtests/{backtest_id}/equity.csv

**Purpose:** Equity points as CSV. Columns: `ts, equity, drawdown`.
**Errors:** 404.

#### GET /api/backtests/{backtest_id}/metrics.csv

**Purpose:** Single-row metrics CSV. Columns mirror `RunMetricsRead`.
**Errors:** 404 if run or metrics missing.

---

### Data quality (`backend/app/api/data_quality.py`)

Router prefix: `/backtests`.

#### GET /api/backtests/{backtest_id}/data-quality

**Purpose:** Deterministic data-quality report for the bars covering the run. Pure arithmetic — no ML, no external calls.
**Response 200 (`DataQualityReportRead`):**

```
{
  "backtest_run_id": int,
  "symbol": str,
  "dataset_status": "ok" | "missing" | "partial",
  "total_bars": int,
  "first_bar_ts": str | null,         # ISO; null if no bars on disk
  "last_bar_ts": str | null,
  "reliability_score": int,           # 0-100
  "issues": list[DataQualityIssue],
  "deferred_checks": list[str]        # human-readable "awaits Phase 3+" notes
}
```

**`DataQualityIssue`:**

```
{
  "category": str,
  "severity": "low" | "medium" | "high",
  "message": str,
  "count": int,
  "affected_range": str | null,
  "distort_backtest": str             # default "unknown"
}
```

**Errors:** 404 if run missing.

---

### Datasets (`backend/app/api/datasets.py`)

Router prefix: `/datasets`.

#### GET /api/datasets

**Purpose:** Filtered list of registered datasets (one row per warehouse file/partition). Cached against the on-disk warehouse — call `POST /datasets/scan` after the ingester runs to refresh.
**Query params (all optional):** `symbol`, `schema`, `source`, `kind`, `dataset_code`. Equality match on each.
**Response 200:** `list[DatasetRead]`
**`DatasetRead`:**

```
{
  "id": int,
  "file_path": str,
  "dataset_code": str,                # e.g. "GLBX.MDP3"
  "schema": str,                      # JSON key is "schema"; field on the model is data_schema (alias)
  "symbol": str | null,
  "source": str,                      # "live" | "historical" | "imported"
  "kind": str,                        # "dbn" | "parquet"
  "start_ts": datetime | null,
  "end_ts": datetime | null,
  "file_size_bytes": int,
  "row_count": int | null,
  "sha256": str | null,
  "last_seen_at": datetime,
  "created_at": datetime
}
```

#### POST /api/datasets/scan

**Purpose:** Walk `BS_DATA_ROOT` (env var; default `C:/data` on Windows, `./data` elsewhere) and reconcile the `datasets` table against disk. Files whose mtime is within 60s are skipped (in-progress writes). Idempotent.
**Request body:** none.
**Response 200 (`DatasetScanResult`):**

```
{
  "scanned": int,                     # files walked
  "added": int,                       # new rows inserted
  "updated": int,                     # rows whose size/mtime changed
  "removed": int,                     # rows whose file no longer exists
  "skipped": int,                     # files skipped (recent mtime)
  "errors": list[str]
}
```

**Errors:** 503 if `BS_DATA_ROOT` doesn't exist on disk (with hint to set the env var or run the ingester).

---

### Data health (`backend/app/api/data_health.py`)

Router prefix: `/data-health`.

#### GET /api/data-health

**Purpose:** Single-fetch payload for the `/data-health` page. Aggregates warehouse contents, scheduled-task status (Windows only), and disk space. Cheap — frontend polls every ~30s.
**Response 200 (`DataHealthPayload`):**

```
{
  "warehouse": {
    "schemas": [
      {
        "schema": str,                # e.g. "tbbo", "ohlcv-1m"
        "partition_count": int,
        "total_bytes": int,
        "symbols": list[str],
        "earliest_date": date | null,
        "latest_date": date | null
      },
      ...
    ],
    "last_scan_ts": datetime | null,  # max(datasets.last_seen_at)
    "total_partitions": int,
    "total_bytes": int
  },
  "scheduled_tasks": [                # empty list on non-Windows hosts
    {
      "name": str,                    # e.g. "BacktestStation-LiveTradesImport"
      "last_run_ts": datetime | null,
      "last_result": int | null,      # 0 = ok, nonzero = exit code
      "last_result_label": str,       # "ok" | "failed" | "never_run" | "unknown"
      "next_run_ts": datetime | null,
      "state": str | null             # "Ready" | "Running" | "Disabled"
    }
  ],
  "scheduled_tasks_supported": bool,  # false on non-Windows
  "disk": { "path": str, "free_bytes": int, "used_bytes": int, "total_bytes": int },
  "fetched_at": datetime
}
```

---

### Autopsy (`backend/app/api/autopsy.py`)

Router prefix: `/backtests`.

#### GET /api/backtests/{backtest_id}/autopsy

**Purpose:** Deterministic post-mortem of a run. No LLM.
**Response 200 (`AutopsyReportRead`):**

```
{
  "backtest_run_id": int,
  "overall_verdict": str,                                   # one-sentence summary
  "edge_confidence": int,                                   # 0..100
  "go_live_recommendation": "not_ready" | "forward_test_only" | "small_size" | "validated",
  "strengths": list[str],
  "weaknesses": list[str],
  "overfitting_warnings": list[str],
  "risk_notes": list[str],
  "suggested_next_test": str,
  "best_conditions": list[AutopsyConditionSlice],
  "worst_conditions": list[AutopsyConditionSlice]
}
```

**`AutopsyConditionSlice`:**

```
{ "label": str, "trades": int, "net_r": float, "win_rate": float | null }
```

Slices group by hour-of-day, weekday, and side.
**Errors:** 404 if run missing.

---

### Notes (`backend/app/api/notes.py`)

Router prefix: `/notes`. Notes attach to any combination of strategy / strategy version / backtest run / trade.

#### GET /api/notes/types

**Purpose:** Note-type vocabulary.
**Response 200 (`NoteTypesRead`):**

```
{ "types": ["observation", "hypothesis", "question", "decision", "bug", "risk_note"] }
```

#### POST /api/notes

**Purpose:** Create a note. At least one attachment can be set; all four can be null (a free-floating note). Each FK that is set is validated to exist or 422.
**Request body (`NoteCreate`):**

```
{
  "body": str,                                   # required, non-empty
  "note_type": str,                              # default "observation"; must be in NOTE_TYPES
  "tags": list[str] | null,                      # trimmed, deduped, empties dropped
  "strategy_id": int | null,
  "strategy_version_id": int | null,
  "backtest_run_id": int | null,
  "trade_id": int | null
}
```

Extra fields rejected.
**Response 201:** `NoteRead`. **Errors:** 422 on missing FK or invalid `note_type`.

#### GET /api/notes

**Purpose:** Filtered list, newest first.
**Query params (all optional, AND'd):** `strategy_id`, `strategy_version_id`, `backtest_run_id`, `trade_id`, `note_type`, `tag` (single tag, post-filter in Python).
**Response 200:** `list[NoteRead]`
**`NoteRead`:**

```
{
  "id": int,
  "strategy_id": int | null,
  "strategy_version_id": int | null,
  "backtest_run_id": int | null,
  "trade_id": int | null,
  "note_type": str,
  "tags": list[str] | null,
  "body": str,
  "created_at": datetime,
  "updated_at": datetime | null
}
```

**Errors:** 422 if `note_type` isn't in NOTE_TYPES.

#### PATCH /api/notes/{note_id}

**Purpose:** Edit body / type / tags. Cannot move a note between attachments — delete and recreate for that.
**Request body (`NoteUpdate`):** all optional: `body`, `note_type`, `tags`. Extra rejected.
**Response 200:** `NoteRead`. **Errors:** 404, 422.

#### DELETE /api/notes/{note_id}

**Response:** 204. **Errors:** 404.

---

### Experiments (`backend/app/api/experiments.py`)

Router prefix: `/experiments`.

#### GET /api/experiments/decisions

**Purpose:** Decision vocabulary.
**Response 200 (`ExperimentDecisionsRead`):**

```
{ "decisions": ["pending", "promote", "reject", "retest", "forward_test", "archive"] }
```

#### POST /api/experiments

**Purpose:** Create an experiment.
**Request body (`ExperimentCreate`):**

```
{
  "strategy_version_id": int,                    # required
  "hypothesis": str,                             # required, non-empty
  "baseline_run_id": int | null,
  "variant_run_id": int | null,
  "change_description": str | null,              # markdown
  "decision": str,                               # default "pending"; must be in EXPERIMENT_DECISIONS
  "notes": str | null
}
```

Extra rejected.
**Response 201:** `ExperimentRead`.
**Errors:** 422 if version missing; 422 if either run missing OR if a run belongs to a different parent strategy than the experiment's version.

#### GET /api/experiments

**Purpose:** Filtered list.
**Query params (all optional, AND'd):** `strategy_version_id`, `strategy_id` (joins via StrategyVersion to filter across all versions of the strategy), `decision`.
**Response 200:** `list[ExperimentRead]`.
**`ExperimentRead`:**

```
{
  "id": int,
  "strategy_version_id": int,
  "hypothesis": str,
  "baseline_run_id": int | null,
  "variant_run_id": int | null,
  "change_description": str | null,
  "decision": str,
  "notes": str | null,
  "created_at": datetime,
  "updated_at": datetime | null
}
```

#### GET /api/experiments/{experiment_id}

**Response 200:** `ExperimentRead`. **Errors:** 404.

#### PATCH /api/experiments/{experiment_id}

**Request body (`ExperimentUpdate`):** all fields optional: `hypothesis`, `baseline_run_id`, `variant_run_id`, `change_description`, `decision`, `notes`. Same cross-strategy validation on the run IDs as POST.
**Response 200:** `ExperimentRead`. **Errors:** 404, 422.

#### DELETE /api/experiments/{experiment_id}

**Response:** 204. **Errors:** 404.

---

### Prompts (`backend/app/api/prompts.py`)

Router prefix: `/prompts`. AI Prompt Generator. The endpoint bundles strategy context into a markdown blob the user copies into Claude/GPT externally. **No LLM calls from inside the app** — model-agnostic by design.

#### GET /api/prompts/modes

**Purpose:** Mode vocabulary for the picker.
**Response 200 (`PromptModesRead`):**

```
{ "modes": ["researcher", "critic", "statistician", "risk_manager", "engineer", "live_monitor"] }
```

#### POST /api/prompts/generate

**Purpose:** Build a copyable prompt for a given strategy + mode.
**Request body (`PromptGenerateRequest`):**

```
{
  "strategy_id": int,
  "mode": str,                       # default "researcher"; must be in PROMPT_MODES
  "focus_question": str | null       # optional, trimmed
}
```

Extra rejected.
**Response 200 (`PromptGenerateResponse`):**

```
{
  "prompt_text": str,                # full markdown blob, ready to paste
  "mode": str,
  "strategy_id": int,
  "bundled_context_summary": list[str],   # diagnostic, e.g. ["3 versions", "12 notes", "2 experiments"]
  "char_count": int
}
```

**Errors:** 404 if strategy missing.

---

### Prop firm (`backend/app/api/prop_firm.py`)

Two routers:

- `router` mounted at `/api/prop-firm`
- `backtest_router` mounted at `/api/backtests` (single-path simulator endpoint)

#### GET /api/prop-firm/profiles

**Purpose:** List firm rule profiles. Active by default.
**Query params:** `include_archived: bool` (default false).
**Response 200:** `list[FirmRuleProfileRead]`.
**`FirmRuleProfileRead`:**

```
{
  "id": int,
  "profile_id": str,                  # slug; this is the foreign key everyone references
  "firm_name": str,
  "account_name": str,
  "account_size": float,
  "phase_type": str,                  # "evaluation" | "funded" | "payout"
  "profit_target": float,
  "max_drawdown": float,
  "daily_loss_limit": float | null,
  "trailing_drawdown_enabled": bool,
  "trailing_drawdown_type": str,      # "intraday" | "end_of_day" | "static" | "none"
  "consistency_pct": float | null,    # 0..1 fraction
  "consistency_rule_type": str,       # "best_day_pct_of_total" | "min_trading_days" | "max_daily_swing" | "none"
  "max_trades_per_day": int | null,
  "minimum_trading_days": int | null,
  "risk_per_trade_dollars": float,
  "payout_split": float,              # 0..1
  "payout_min_days": int | null,
  "payout_min_profit": float | null,
  "eval_fee": float,
  "activation_fee": float,
  "reset_fee": float,
  "monthly_fee": float,
  "source_url": str | null,
  "last_known_at": str | null,        # date-ish string (not parsed)
  "notes": str | null,
  "verification_status": str,         # "verified" | "unverified" | "demo"
  "verified_at": datetime | null,
  "verified_by": str | null,
  "is_seed": bool,                    # True if seeded from PRESETS dict
  "is_archived": bool,
  "created_at": datetime | null,
  "updated_at": datetime | null
}
```

#### GET /api/prop-firm/profiles/{profile_id}

Note: `profile_id` is the slug string, not the int `id`.
**Response 200:** `FirmRuleProfileRead`. **Errors:** 404.

#### POST /api/prop-firm/profiles

**Purpose:** Create a custom (non-seed) firm profile.
**Request body (`FirmRuleProfileCreate`):** Required: `profile_id`, `firm_name`, `account_name`, `account_size`, `profit_target`, `max_drawdown`. Optional defaults: `daily_loss_limit=null`, `trailing_drawdown_enabled=true`, `trailing_drawdown_type="intraday"`, `consistency_pct=null`, `consistency_rule_type="none"`, `max_trades_per_day=null`, `minimum_trading_days=null`, `risk_per_trade_dollars=200.0`, `payout_split=0.9`, `payout_min_days=null`, `payout_min_profit=null`, `eval_fee=0`, `activation_fee=0`, `reset_fee=0`, `monthly_fee=0`, `source_url=null`, `last_known_at=null`, `notes=null`, `phase_type="evaluation"`. `is_seed=False` and `verification_status="unverified"` are forced server-side. Extra rejected.
**Response 201:** `FirmRuleProfileRead`. **Errors:** 409 if `profile_id` already exists.

#### PATCH /api/prop-firm/profiles/{profile_id}

**Purpose:** Partial update. Pydantic v2 distinguishes "field omitted" from "field set to null" — important for `daily_loss_limit` (null disables the rule).
**Request body (`FirmRuleProfilePatch`):** every field optional. Setting `verification_status="verified"` stamps `verified_at = now()`. Editing any rule field on a verified profile auto-flips status back to `"unverified"` and clears stamps. Editing only `notes` / `source_url` / `verified_by` keeps verification.
**Response 200:** `FirmRuleProfileRead`. **Errors:** 404.

#### POST /api/prop-firm/profiles/{profile_id}/reset

**Purpose:** Restore a seed profile to the static `PRESETS` factory values.
**Request body:** none.
**Response 200:** `FirmRuleProfileRead`.
**Errors:** 404 if profile is user-created (not a seed) or if the seed key has been removed from `PRESETS`.

#### POST /api/prop-firm/profiles/{profile_id}/archive

**Response 200:** `FirmRuleProfileRead`. **Errors:** 404.

#### POST /api/prop-firm/profiles/{profile_id}/unarchive

**Response 200:** `FirmRuleProfileRead`. **Errors:** 404.

#### GET /api/prop-firm/presets

**Purpose:** Legacy lean preset shape, used by the deterministic single-path simulator embedded on `/backtests/[id]`. Reads from the active (non-archived) DB rows.
**Response 200:** `list[PropFirmPresetRead]`

```
{
  "key": str,                         # = profile_id
  "name": str,
  "notes": str,
  "starting_balance": float,
  "profit_target": float,
  "max_drawdown": float,
  "trailing_drawdown": bool,
  "daily_loss_limit": float | null,
  "consistency_pct": float | null,
  "max_trades_per_day": int | null,
  "risk_per_trade_dollars": float,
  "trailing_drawdown_type": str,      # default "none"
  "minimum_trading_days": int | null,
  "payout_split": float,              # default 0.9
  "payout_min_days": int | null,
  "payout_min_profit": float | null,
  "eval_fee": float,
  "activation_fee": float,
  "reset_fee": float,
  "monthly_fee": float,
  "source_url": str | null,
  "last_known_at": str | null
}
```

#### GET /api/prop-firm/simulations

**Purpose:** List all Monte Carlo simulation runs, newest first.
**Response 200:** `list[SimulationRunListRow]`

```
{
  "simulation_id": str,               # int primary key, stringified
  "name": str,
  "strategy_name": str,
  "backtests_used": int,
  "firm_name": str,
  "account_size": float,
  "sampling_mode": "trade_bootstrap" | "day_bootstrap" | "regime_bootstrap",
  "simulation_count": int,
  "risk_label": str,                  # e.g. "$200" or "sweep"
  "pass_rate": float,                 # 0..1
  "fail_rate": float,
  "payout_rate": float,
  "ev_after_fees": float,
  "confidence": float,
  "created_at": str                   # ISO seconds
}
```

#### GET /api/prop-firm/simulations/{sim_id}

Note: `sim_id` is the int primary key.
**Purpose:** Full simulation detail.
**Response 200:** `SimulationRunDetail` — see Section 6 for full sub-shapes. Top-level keys:

```
{
  "config": SimulationRunConfigOut,
  "firm": FirmRuleProfile,                          # full editable shape
  "pool_backtests": list[PoolBacktestSummary],
  "aggregated": SimulationAggregatedStats,
  "risk_sweep": list[RiskSweepRow] | null,
  "selected_paths": list[SelectedPath],             # 5 buckets: best/worst/median/near_fail/near_pass
  "fan_bands": FanBands,                            # equity-curve percentile bands
  "rule_violation_counts": dict[str, int],
  "confidence": SimulatorConfidenceScore,
  "daily_pnl": list[DailyPnL]
}
```

**Errors:** 404.

#### POST /api/prop-firm/simulations

**Purpose:** Run a new Monte Carlo prop-firm simulation. **Long-running** — allocates and runs N (default 500, max 10,000) sequence simulations against the full bootstrap pool. Synchronous.
**Request body (`SimulationRunRequest`):**

```
{
  "name": str,                                              # required, max 120
  "selected_backtest_ids": list[int],                       # required, min 1; the trade pool
  "firm_profile_id": str,                                   # required slug
  "account_size": float,                                    # required, > 0
  "starting_balance": float,                                # required, > 0
  "phase_mode": "eval_only" | "funded_only" | "eval_to_payout",   # default "eval_only"

  "sampling_mode": "trade_bootstrap" | "day_bootstrap" | "regime_bootstrap",  # default "trade_bootstrap"
  "simulation_count": int,                                  # default 500, range [10, 10000]
  "max_trades_per_sequence": int | null,
  "max_days_per_sequence": int | null,
  "use_replacement": bool,                                  # default true
  "random_seed": int,                                       # default 42

  "risk_mode": "fixed_dollar" | "fixed_contracts" | "percent_balance" | "risk_sweep",  # default "fixed_dollar"
  "risk_per_trade": float | null,                           # default 200.0
  "risk_sweep_values": list[float] | null,

  "commission_override": float | null,
  "slippage_override": float | null,

  "daily_trade_limit": int | null,
  "daily_loss_stop": float | null,
  "daily_profit_stop": float | null,
  "walkaway_after_winner": bool,                            # default false
  "reduce_risk_after_loss": bool,                           # default false
  "max_losses_per_day": int | null,
  "copy_trade_accounts": int,                               # default 1

  "fees_enabled": bool,                                     # default true
  "payout_rules_enabled": bool,                             # default true
  "notes": str                                              # default ""
}
```

Extra rejected.
**Response 201:** `SimulationRunDetail` (same shape as GET).
**Errors:** 404 if any backtest or firm profile missing. 422 if pool has zero trades.

#### POST /api/backtests/{backtest_id}/prop-firm-sim

**Purpose:** Single-path deterministic prop-firm checker (no Monte Carlo). Runs the trades through one firm config in chronological order and reports pass/fail.
**Request body (`PropFirmConfigIn`):**

```
{
  "starting_balance": float,                # > 0
  "profit_target": float,                   # > 0
  "max_drawdown": float,                    # > 0
  "trailing_drawdown": bool,                # default true
  "daily_loss_limit": float | null,         # > 0 if set
  "consistency_pct": float | null,          # (0, 1] if set
  "max_trades_per_day": int | null,         # > 0 if set
  "risk_per_trade_dollars": float           # > 0
}
```

Extra rejected.
**Response 200 (`PropFirmResultRead`):**

```
{
  "passed": bool,
  "fail_reason": str | null,
  "days_simulated": int,
  "days_to_pass": int | null,
  "max_drawdown_reached": float,
  "peak_balance": float,
  "final_balance": float,
  "total_profit": float,
  "best_day": PropFirmDayRow | null,
  "worst_day": PropFirmDayRow | null,
  "consistency_ok": bool | null,
  "best_day_share_of_profit": float | null,
  "total_trades": int,
  "skipped_trades_no_r": int,
  "days": list[PropFirmDayRow]
}
```

**`PropFirmDayRow`:** `{ "date": str, "pnl": float, "trades": int, "balance_at_eod": float }`.
**Errors:** 404.

---

### Risk profiles (`backend/app/api/risk_profiles.py`)

Router prefix: `/risk-profiles`.

#### GET /api/risk-profiles/statuses

**Response 200 (`RiskProfileStatusesRead`):** `{ "statuses": ["active", "archived"] }`.

#### GET /api/risk-profiles

**Purpose:** All profiles, newest first.
**Response 200:** `list[RiskProfileRead]`
**`RiskProfileRead`:**

```
{
  "id": int,
  "name": str,
  "status": str,                              # "active" | "archived"
  "max_daily_loss_r": float | null,           # caps in R-multiples; null = no cap
  "max_drawdown_r": float | null,
  "max_consecutive_losses": int | null,
  "max_position_size": int | null,
  "allowed_hours": list[int] | null,          # UTC hours 0..23, sorted, deduped; null = any hour
  "notes": str | null,
  "strategy_params": dict | null,             # prefill values for the run-a-backtest form
  "created_at": datetime,
  "updated_at": datetime
}
```

#### POST /api/risk-profiles

**Request body (`RiskProfileCreate`):**

```
{
  "name": str,                                # required, max 120
  "status": str,                              # default "active"
  "max_daily_loss_r": float | null,
  "max_drawdown_r": float | null,
  "max_consecutive_losses": int | null,
  "max_position_size": int | null,
  "allowed_hours": list[int] | null,          # entries must be 0..23
  "notes": str | null,
  "strategy_params": dict | null
}
```

Extra rejected.
**Response 201:** `RiskProfileRead`. **Errors:** 409 if name exists. 422 if any `allowed_hours` entry is out of range.

#### GET /api/risk-profiles/{profile_id}

**Response 200:** `RiskProfileRead`. **Errors:** 404.

#### PATCH /api/risk-profiles/{profile_id}

**Request body (`RiskProfileUpdate`):** every field optional; same validators. Extra rejected.
**Response 200:** `RiskProfileRead`. **Errors:** 404, 409 (name collision), 422.

#### DELETE /api/risk-profiles/{profile_id}

**Response:** 204. **Errors:** 404.

#### POST /api/risk-profiles/{profile_id}/evaluate

**Purpose:** Walk a backtest run's trades through the profile and report cap violations. Read-only — does not mutate the profile or the run.
**Query params:** `run_id: int` (required; not in body).
**Request body:** none.
**Response 200 (`RiskEvaluationRead`):**

```
{
  "profile_id": int,
  "run_id": int,
  "total_trades_evaluated": int,
  "violations": [
    {
      "kind": str,                            # "daily_loss" | "drawdown" | "consecutive_losses" | "position_size" | "hour_window"
      "at_trade_id": int,
      "at_trade_index": int,                  # zero-based, entry-time order
      "message": str
    }
  ]
}
```

**Errors:** 404 if profile or run missing.

---

### Settings (`backend/app/api/settings.py`)

Router prefix: `/settings`. Read-only inspection. **No editable user prefs yet.**

#### GET /api/settings/system

**Response 200 (`SystemSettingsRead`):**

```
{
  "bs_data_root": str,                # path string
  "bs_data_root_exists": bool,
  "databento_api_key_set": bool,      # never the actual key
  "version": str,                     # e.g. "0.1.0"
  "git_sha": str | null,              # short SHA; null if not a git checkout
  "git_dirty": bool,
  "platform": str,                    # sys.platform: "win32" | "darwin" | "linux"
  "python_version": str,              # "3.12.x"
  "free_disk_bytes": int,
  "server_time_utc": datetime,
  "server_time_et": datetime          # America/New_York
}
```

No persistence — every field is read live from process state.

---

### Monitor (`backend/app/api/monitor.py`)

Router prefix: `/monitor`. Sources are local files written by the live bot + ingester + import scheduler, plus the latest live `BacktestRun`.

#### GET /api/monitor/live

**Purpose:** Snapshot of the running bot's last heartbeat. The backend reads `LIVE_STATUS_PATH` from disk and normalizes loose key spellings (`status` vs `strategy_status`, etc.).
**Response 200 (`LiveMonitorStatus`):**

```
{
  "source_path": str,
  "source_exists": bool,
  "strategy_status": str,                     # "missing" if file absent; otherwise free string
  "last_heartbeat": datetime | null,
  "current_symbol": str | null,
  "current_session": str | null,
  "today_pnl": float | null,
  "today_r": float | null,
  "trades_today": int | null,
  "last_signal": dict | str | null,           # whatever the bot wrote
  "last_error": str | null,
  "raw": dict | null                          # passthrough of the raw JSON for debug
}
```

**Errors:** 422 if the file exists but is malformed JSON.

#### GET /api/monitor/ingester

**Purpose:** Live tick ingester's heartbeat. 404 means "ingester not running or never run".
**Response 200 (`IngesterStatus`):**

```
{
  "status": str,                              # "running" | "error"
  "started_at": datetime,
  "uptime_seconds": int,
  "last_tick_ts": datetime | null,
  "ticks_received": int,
  "ticks_last_60s": int,
  "current_file": str | null,
  "current_date": str | null,
  "symbols": list[str],
  "dataset": str,
  "schema": str,                              # JSON key is "schema"; field is data_schema (alias)
  "stype_in": str,
  "reconnect_count": int,
  "last_error": str | null
}
```

**Errors:** 404 if heartbeat file missing. 422 if malformed.

#### GET /api/monitor/live-trades

**Purpose:** Health snapshot of the daily live-trades import pipeline. Designed to surface silent failures — e.g. importer logs `errors=0` but produces no run.
**Response 200 (`LiveTradesPipelineStatus`):**

```
{
  "last_run_id": int | null,                  # latest BacktestRun(source="live")
  "last_run_name": str | null,
  "last_run_imported_at": datetime | null,
  "last_trade_ts": datetime | null,
  "trade_count": int | null,

  "inbox_dir": str,
  "inbox_jsonl_exists": bool,
  "inbox_jsonl_size_bytes": int | null,
  "inbox_jsonl_modified_at": datetime | null,

  "import_log_path": str,
  "import_log_exists": bool,
  "import_log_modified_at": datetime | null,
  "import_log_last_status": "ok" | "failed" | "no_jsonl" | "running" | "unknown",
  "import_log_tail": list[str]                # last ~30 lines
}
```

#### GET /api/monitor/signals

**Purpose:** Recent live signals (`live_signals` table) for the session journal panel. Newest first.
**Query params:** `strategy_id: int | null`, `strategy_version_id: int | null`, `since: datetime | null` (ISO; ts >= since), `limit: int` (default 50, range [1, 500]).

- If `strategy_id` is supplied, the endpoint resolves all of that strategy's version IDs and matches `LiveSignal.strategy_version_id IN (those)`. If the strategy has no versions, returns `[]`.
- Filters AND together.
  **Response 200:** `list[LiveSignalRead]`

```
{
  "id": int,
  "strategy_version_id": int | null,
  "ts": datetime,
  "side": str,                                # "long" | "short"
  "price": float,
  "reason": str | null,
  "executed": bool
}
```

#### GET /api/monitor/drift/latest

**Purpose:** Auto-resolve the latest live run, find its strategy version, and compute a drift comparison against that version's baseline. Saves the frontend a round-trip.
**Response 200:** `DriftComparisonRead` (see below).
**Errors:** 404 if no live runs exist. 404 with explanatory detail if the resolved version has no baseline assigned.

#### GET /api/monitor/drift/{strategy_version_id}

**Purpose:** Forward Drift Monitor signals for a specific version. Resolves the version's `baseline_run_id` and the most-recent live run, then runs the drift signals (win-rate + entry-time chi-square).

- "No live run yet" is **not** a 404 — the endpoint still returns a payload with the live-run-empty case surfaced as WARN results so the UI can render the panel.
  **Response 200 (`DriftComparisonRead`):**

```
{
  "strategy_version_id": int,
  "baseline_run_id": int,
  "live_run_id": int | null,
  "computed_at": datetime,
  "results": [
    {
      "signal_type": str,                     # currently "win_rate" or "entry_time"
      "status": "OK" | "WATCH" | "WARN",
      "live_value": float | null,
      "baseline_value": float | null,
      "deviation": float | null,
      "sample_size_live": int,
      "sample_size_baseline": int,
      "incomplete": bool,                     # sample below threshold for reliable read
      "message": str
    },
    ...
  ]
}
```

**Errors:** 404 if version missing or no baseline assigned.

---

### Replay (`backend/app/api/replay.py`)

Router prefix: `/replay`.

#### GET /api/replay/{symbol}/{date}

**Purpose:** One trading day's 1-minute candles for `symbol`, plus optional run-overlay markers, plus auto-detected FVG zones over resampled 5-minute candles.
**Path params:** `symbol` (string), `date` (ISO `YYYY-MM-DD`).
**Query params:** `backtest_run_id: int | null`. If supplied, only trades whose `entry_ts` falls inside `[date 00:00 UTC, date+1 00:00 UTC)` are included.
**Response 200 (`ReplayPayload`):**

```
{
  "symbol": str,
  "date": "YYYY-MM-DD",
  "bars": [
    {
      "ts": datetime,                         # ISO UTC
      "open": float, "high": float, "low": float, "close": float,
      "volume": int
    },
    ...
  ],
  "entries": [
    {
      "trade_id": int,
      "entry_ts": datetime,
      "exit_ts": datetime | null,
      "side": str,                            # "long" | "short"
      "entry_price": float,
      "exit_price": float | null,
      "stop_price": float | null,
      "target_price": float | null,
      "pnl": float | null,
      "r_multiple": float | null,
      "exit_reason": str | null
    },
    ...
  ],
  "backtest_run_id": int | null,
  "fvg_zones": [
    {
      "direction": "BULLISH" | "BEARISH",
      "low": float,
      "high": float,
      "created_at": datetime,
      "timeframe": str,                       # currently "5m"
      "filled": bool,
      "fill_time": datetime | null
    },
    ...
  ]
}
```

FVG zones are skipped silently if there are fewer than 3 5-minute candles for the day.
**Errors:** 404 if `backtest_run_id` is supplied but the run doesn't exist.
**Notes:** Tick-level granularity is intentionally NOT in this endpoint (use `/trade-replay`).

---

### Trade replay (`backend/app/api/trade_replay.py`)

Router prefix: `/trade-replay`. Live-trade-only (engine + imported runs are not surfaced here).

#### GET /api/trade-replay/runs

**Purpose:** All `BacktestRun(source="live")` runs with their trades for the picker.
**Response 200:** `list[TradeReplayRunRead]`

```
{
  "run_id": int,
  "run_name": str | null,
  "symbol": str,
  "start_ts": datetime | null,
  "end_ts": datetime | null,
  "trades": [
    {
      "trade_id": int,
      "entry_ts": datetime,
      "exit_ts": datetime | null,
      "side": str,
      "entry_price": float,
      "exit_price": float | null,
      "stop_price": float | null,
      "target_price": float | null,
      "r_multiple": float | null,
      "pnl": float | null,
      "exit_reason": str | null,
      "tbbo_available": bool                  # disk check; false = render the row disabled
    },
    ...
  ]
}
```

#### GET /api/trade-replay/{run_id}/{trade_id}/ticks

**Purpose:** Windowed TBBO ticks around one anchored trade.
**Query params:** `lead_seconds: int` (default `LEAD_DEFAULT_SECONDS` from the service, range `[0, LEAD_MAX_SECONDS]`); `trail_seconds: int` (same pattern with `TRAIL_*`).
**Response 200 (`TradeReplayWindowRead`):**

```
{
  "trade_id": int,
  "symbol": str,
  "window_start": datetime,
  "window_end": datetime,
  "anchor": {
    "entry_ts": datetime,
    "exit_ts": datetime | null,
    "side": str,
    "entry_price": float,
    "exit_price": float | null,
    "stop_price": float | null,
    "target_price": float | null,
    "r_multiple": float | null
  },
  "ticks": [
    {
      "ts": datetime,
      "bid_px": float | null,
      "ask_px": float | null,
      "trade_px": float | null,                # populated only when action="T"
      "trade_size": int | null,
      "side": str | null                       # "A" | "B" | "N"
    },
    ...
  ]
}
```

**Errors:** 404 if run missing, run is not source="live", trade missing or in a different run, or the TBBO partition for that date doesn't exist on disk.

---

## 4. Long-running operations / streaming

There is no streaming today. **No WebSockets, no Server-Sent Events, no async job queue, no background polling pattern.** Three implications:

1. **Synchronous slow endpoints.** The frontend must show a loading state and disable the form until the response returns:
   - `POST /api/backtests/run` — runs the engine end-to-end. Seconds to minutes depending on date range.
   - `POST /api/prop-firm/simulations` — runs Monte Carlo (default 500 sequences, max 10,000). Likely seconds to a minute.
   - `POST /api/datasets/scan` — walks the warehouse on disk. Should be fast unless the warehouse is huge.

2. **Polling for live data.** The `/monitor` page is expected to poll. Suggested intervals based on existing comments:
   - `/api/data-health`: ~30s
   - `/api/monitor/live`, `/api/monitor/ingester`, `/api/monitor/live-trades`: similarly polling-driven; no exact interval specified

3. **Multipart upload.** `POST /api/import/backtest` is the only multipart endpoint. Files are read into memory (`await file.read().decode("utf-8-sig")`) — large files would blow memory but the use case is small CSVs.

**File downloads (CSV):**

- `GET /api/backtests/{id}/trades.csv`
- `GET /api/backtests/{id}/equity.csv`
- `GET /api/backtests/{id}/metrics.csv`

All return `Content-Type: text/csv` with a `Content-Disposition: attachment; filename="..."` header. Standard browser-driven download is fine.

---

## 5. Critical workflows

### 5.1. Import an existing backtest result bundle

1. User picks files (`trades_file`, `equity_file`, plus optional metrics + config) and metadata (strategy slug, version, symbol, etc.).
2. Frontend issues `POST /api/import/backtest` as `multipart/form-data`.
3. Backend creates (or matches) a Strategy + StrategyVersion if `strategy_slug` doesn't exist, parses files, persists `BacktestRun` + `Trade` rows + `EquityPoint` rows + optional `RunMetrics` + optional `ConfigSnapshot`.
4. Response is `ImportBacktestResponse` with the new `backtest_id`. Frontend navigates to `/backtests/{backtest_id}`.

### 5.2. Run an engine backtest

1. Frontend `GET /api/backtests/strategies` to populate the strategy dropdown and per-strategy parameter forms.
2. (Optional) `GET /api/strategies` and `GET /api/strategies/{id}` to pick the existing `strategy_version_id`.
3. (Optional) `GET /api/risk-profiles` — if the user picks a profile, prefill `params` from `strategy_params`.
4. Frontend `POST /api/backtests/run` with the full body. Disable the form and show a spinner.
5. On 201, response is the freshly-created `BacktestRunRead`. Navigate to `/backtests/{id}`.
6. On 422, surface the `detail` string (covers "no bars found", "strategy resolver failed", date validation).

### 5.3. View a backtest's full result

The detail page typically issues these in parallel:

- `GET /api/backtests/{id}` — header info
- `GET /api/backtests/{id}/metrics` — stats card
- `GET /api/backtests/{id}/equity` — equity curve
- `GET /api/backtests/{id}/trades` — trade table
- `GET /api/backtests/{id}/config` — config panel (may 404 on legacy imports)
- `GET /api/backtests/{id}/autopsy` — autopsy report
- `GET /api/backtests/{id}/data-quality` — data-quality issues
- `GET /api/notes?backtest_run_id={id}` — attached notes

Tag editing: `PUT /api/backtests/{id}/tags`. Rename: `PATCH /api/backtests/{id}`. Delete: `DELETE /api/backtests/{id}`.

### 5.4. Compare two backtests (Experiment Ledger)

There is no dedicated "compare two runs" endpoint. The compare UI is implemented client-side by fetching both runs' metrics, trades, and equity curves and rendering them side by side. Wrap the comparison in an experiment for tracking:

1. From the strategy dossier, `POST /api/experiments` with `strategy_version_id`, `hypothesis`, `baseline_run_id` (the original), `variant_run_id` (the new), `change_description` (markdown).
2. Both run IDs are validated to belong to the same parent strategy.
3. Decision starts as `pending`. After review, `PATCH /api/experiments/{id}` with `decision="promote"|"reject"|"retest"|"forward_test"|"archive"`.

### 5.5. Run a prop-firm Monte Carlo simulation

1. Frontend lists firm profiles via `GET /api/prop-firm/profiles` (and optionally `GET /api/prop-firm/profiles/{profile_id}` for the editor).
2. Frontend lists candidate backtests via `GET /api/strategies/{id}/runs` or `GET /api/backtests`.
3. User configures `name`, `selected_backtest_ids`, `firm_profile_id`, `account_size`, `starting_balance`, sampling mode, simulation count, risk mode, etc.
4. Frontend `POST /api/prop-firm/simulations`. Synchronous — show a progress UI.
5. Response is the full `SimulationRunDetail`. Navigate to the detail page using `simulation_id` (note: this is the integer PK as a string).
6. List page: `GET /api/prop-firm/simulations` — table rows.

### 5.6. Forward Drift monitoring

1. From a strategy dossier, `PATCH /api/strategy-versions/{version_id}/baseline` with `{"run_id": <some imported or engine run>}`.
2. The Monitor page calls `GET /api/monitor/drift/latest` to auto-resolve (latest live run → its version → drift comparison) or `GET /api/monitor/drift/{version_id}` for a specific version.
3. Render each `DriftResultRead` as a tri-color (OK/WATCH/WARN) panel. Note the `incomplete` flag for "tentative" hint badges.

### 5.7. AI Prompt Generator

1. `GET /api/prompts/modes` to populate the mode picker.
2. User picks a strategy + mode, optional focus question.
3. `POST /api/prompts/generate` returns `prompt_text` (markdown blob) and `bundled_context_summary` (diagnostic list of what got included).
4. Frontend offers a "Copy to clipboard" button. The user pastes into Claude/GPT externally — **the backend never calls an LLM.**

---

## 6. Data shapes the designer will repeatedly see

### Bar / candle (`ReplayBar`)

```
{ "ts": datetime, "open": float, "high": float, "low": float, "close": float, "volume": int }
```

### Trade (`TradeRead`)

See full shape under `GET /api/backtests/{id}/trades`. Repeated in `ReplayEntry` (without `symbol`/`size`/`tags`) and `TradeReplayTradeRead` (with `tbbo_available`).

### Backtest summary stats (`RunMetricsRead`)

```
net_pnl, net_r, win_rate (0..1), profit_factor, max_drawdown,
avg_r, avg_win, avg_loss, trade_count,
longest_losing_streak, best_trade, worst_trade
```

All fields nullable — legacy imports may lack metrics.

### Equity curve point (`EquityPointRead`)

```
{ "id": int, "backtest_run_id": int, "ts": datetime, "equity": float, "drawdown": float | null }
```

There are **no signal/setup endpoints** in the current backend. The `live_signals` row (returned by `/monitor/signals`) is the closest:

```
{ "id": int, "strategy_version_id": int | null, "ts": datetime, "side": str, "price": float, "reason": str | null, "executed": bool }
```

### Sweep / Monte Carlo result row (`SimulationRunListRow`)

See full shape under `GET /api/prop-firm/simulations`.

### Monte Carlo detail sub-shapes (used inside `SimulationRunDetail`)

**`SimulationAggregatedStats`** — every distribution stat the dashboard cards render:

```
pass_rate / fail_rate / payout_rate: ConfidenceInterval = { value, low, high }
average_final_balance, median_final_balance, std_dev_final_balance
p10/p25/p75/p90_final_balance
average_days_to_pass: ConfidenceInterval
median_days_to_pass, average_trades_to_pass, median_trades_to_pass
average_max_drawdown, median_max_drawdown, worst_max_drawdown
average_drawdown_usage: ConfidenceInterval
median_drawdown_usage
average_payout, median_payout
expected_value_before_fees
expected_value_after_fees: ConfidenceInterval
std_dev_ev_after_fees, average_fees_paid
most_common_failure_reason: FailureReason | null
daily_loss_failure_rate, trailing_drawdown_failure_rate, consistency_failure_rate
profit_target_hit_rate, payout_blocked_rate
final_balance_distribution / ev_after_fees_distribution / max_drawdown_distribution: OutcomeDistribution
```

`OutcomeDistribution = { metric, stats: DistributionStats, buckets: list[DistributionBucket] }` where `DistributionStats` is `{ mean, median, std_dev, min, max, p10, p25, p75, p90, iqr, spread }` and `DistributionBucket` is `{ range_low, range_high, count }`.

**`SelectedPath`** — sample sequence for the chart:

```
{
  "bucket": "best" | "worst" | "median" | "near_fail" | "near_pass",
  "sequence_number": int,
  "final_status": "passed" | "failed" | "payout_reached" | "expired",
  "days": int,
  "trades": int,
  "ending_balance": float,
  "max_drawdown_usage_percent": float,
  "failure_reason": FailureReason | null,
  "equity_curve": list[float]
}
```

`FailureReason` ∈ `daily_loss_limit | trailing_drawdown | max_drawdown | consistency_rule | payout_blocked | min_days_not_met | account_expired | max_trades_reached | other`.

**`FanBands`:**

```
{ "starting_balance": float, "median": list[float], "p10": list[float], "p25": list[float], "p75": list[float], "p90": list[float] }
```

**`SimulatorConfidenceScore`:**

```
{
  "overall": float,
  "label": "low" | "moderate" | "high" | "very_high",
  "subscores": {
    "monte_carlo_stability": float,
    "trade_pool_quality": float,
    "day_pool_quality": float,
    "firm_rule_accuracy": float,
    "risk_model_accuracy": float,
    "sampling_method_quality": float,
    "backtest_input_quality": float
  },
  "weaknesses": list[str],
  "sequence_count": int,
  "convergence_stability": float
}
```

**`PoolBacktestSummary`:**

```
{
  "backtest_id": int, "strategy_id": int, "strategy_name": str, "strategy_version": str,
  "symbol": str, "market": str, "timeframe": str,
  "start_date": str, "end_date": str,
  "data_source": str, "commission_model": str, "slippage_model": str,
  "initial_balance": float, "confidence_score": float,
  "trade_count": int, "day_count": int
}
```

**`DailyPnL`:** `{ "date": str, "pnl": float, "trades": int }`.

**`RuleViolationEventType`** keys for `rule_violation_counts`: `daily_loss_limit`, `trailing_drawdown`, `profit_target_hit`, `consistency_rule`, `payout_eligible`, `payout_blocked`, `max_contracts_exceeded`, `minimum_days_not_met`.

---

## 7. Frontend integration notes

### Pagination

**There is none.** No `GET` endpoint accepts `limit`/`offset`/`cursor` parameters except:

- `GET /api/monitor/signals` accepts `limit: int` (default 50, max 500), no offset/cursor.

`GET /api/backtests`, `GET /api/strategies`, `GET /api/notes`, `GET /api/experiments`, etc. return the **full list** sorted newest-first. For now this is fine (single-user, small datasets); when run counts grow, this will need pagination retrofitted.

### Sort / filter

Filters are query parameters on the relevant list endpoints, AND'd together. They are equality matches — there is no full-text search, no range filter, no `ilike` partial match. Specific endpoints:

- `GET /api/datasets`: `symbol`, `schema`, `source`, `kind`, `dataset_code`
- `GET /api/notes`: `strategy_id`, `strategy_version_id`, `backtest_run_id`, `trade_id`, `note_type`, `tag`
- `GET /api/experiments`: `strategy_version_id`, `strategy_id`, `decision`
- `GET /api/monitor/signals`: `strategy_id`, `strategy_version_id`, `since`, `limit`
- `GET /api/prop-firm/profiles`: `include_archived`

Client-side sorting/filtering is the assumption for tables.

### Timestamp format

ISO-8601 throughout (FastAPI / Pydantic default). Backend sometimes stores tz-naive UTC (especially for live runs) — be defensive on the frontend: treat any datetime without `Z` or `+offset` as UTC.

CSV exports use Python's `datetime.isoformat()` — same shape.

### Decimal precision

Prices, equity, drawdown, P&L, R-multiples are all `float`. There is no Decimal wrapping. Round client-side per display convention (typically 2 dp for dollars, 2-4 dp for prices, 2 dp for R).

### Error response shape

FastAPI default. On `HTTPException(status_code=N, detail="...")`:

```
{ "detail": "..." }
```

On Pydantic validation errors (422):

```
{ "detail": [ { "loc": [...], "msg": "...", "type": "..." }, ... ] }
```

Most explicit `raise HTTPException(...)` calls in the routers carry a `detail` string crafted for the user — show it directly.

### Caching / ETags

None. No `Cache-Control`, no `ETag` headers anywhere. Frontend caching is its own problem.

### Vocabulary endpoints (recommended pattern)

Every controlled vocabulary is exposed via a small endpoint so the frontend isn't hardcoding strings:

- `/api/strategies/stages` → STRATEGY_STAGES
- `/api/notes/types` → NOTE_TYPES
- `/api/experiments/decisions` → EXPERIMENT_DECISIONS
- `/api/prompts/modes` → PROMPT_MODES
- `/api/risk-profiles/statuses` → RISK_PROFILE_STATUSES

Status enums **not** behind a vocabulary endpoint (because they're load-bearing literals in many shapes):

- `BacktestRun.source`: `"imported" | "engine" | "live"`
- `BacktestRun.status`: `"succeeded" | "failed" | "running"` (string)
- `Dataset.source`: `"live" | "historical" | "imported"`
- `Dataset.kind`: `"dbn" | "parquet"`
- `Trade.exit_reason`: `"stop" | "target" | "eod" | "manual"` (string, may be null)
- Drift `status`: `"OK" | "WATCH" | "WARN"`

### Reserved keys

The Pydantic field `data_schema` is exposed as `schema` in JSON via `Field(alias="schema")` on `DatasetRead` and `IngesterStatus` (the alias avoids shadowing `BaseModel.schema()`). Don't use the literal Python attribute name `data_schema` from the frontend — the wire key is `schema`.

---

## 8. What's NOT in the backend yet

Be explicit so the design avoids dead screens.

- **Auth.** No login, no users, no permissions. A "you" in the UI is the only user.
- **Pagination.** Lists return everything.
- **Async / streaming / WebSockets / SSE.** Long endpoints block. Show spinners, no progress events to subscribe to.
- **Editable user preferences.** `GET /api/settings/system` is read-only and inferred from process state. Theme, contract specs, session hours, keyboard shortcuts — none of these are persisted yet. The schema docstring explicitly says editable prefs are a separate PR.
- **Run status polling.** `BacktestRun.status` rarely shows `"running"` because runs are synchronous today. There is no `GET /api/backtests/{id}/status` endpoint.
- **Engine progress stream.** `POST /api/backtests/run` has no progress callback.
- **Compare-two-runs endpoint.** Frontend assembles the comparison from existing per-run endpoints. Wrap it in an Experiment for tracking.
- **In-app LLM chat.** `/api/prompts/generate` returns markdown for the user to paste externally. No model is called from the backend.
- **Walk-forward / true Monte Carlo robustness lab / overfitting detector / strategy plugin DSL.** Mentioned in roadmap as deferred.
- **Cascade delete with attached data.** `DELETE /api/strategies/{id}` and `DELETE /api/strategy-versions/{id}` refuse with 409 when versions/runs exist. Designers should not show a "Force delete" button — the UX is "Archive" instead (`PATCH status="archived"` for strategies, `PATCH /api/strategy-versions/{id}/archive` for versions).
- **Forward Drift v2 frontend panels.** Backend ships drift signals, but only WR + entry-time are computed. More signals are planned.
- **Strategy plugin discovery.** `GET /api/backtests/strategies` returns a hand-maintained list; there is no auto-registry. Two strategies today (`fractal_amd`, `moving_average_crossover`).
- **Tick-level replay for engine/imported runs.** `/trade-replay` is live-only by design.
- **Unrealized P&L on the live monitor.** Surfaced PnL is realized-only (the bot's heartbeat). Unrealized requires a live quote source not yet wired.
- **Server-side full-text search, range queries, sort params.** Not implemented.
- **Cancel a running backtest / simulation.** No cancellation endpoint. Once submitted, you wait.

If a screen needs any of the above, talk to the user — those are scope decisions, not implementation gaps to paper over with placeholders.

---

## 9. Routers added after 2026-04-29

These routers shipped after the doc's "verified on 2026-04-29" cutoff. Stubbed-in here so the frontend has a contract reference; pull from the actual code if uncertain.

### Knowledge (`backend/app/api/knowledge.py`)

Knowledge-cards CRUD plus vocabulary endpoints. Cards are typed snippets of trading knowledge (concepts, formulas, setups, rules) with optional links to a strategy, a backtest run, a strategy version, or a research entry.

- `GET /api/knowledge/health` — Hygiene snapshot. Counts of stale drafts, trusted-without-evidence, needs_testing-without-runs.
- `GET /api/knowledge/kinds` — Vocabulary: `["concept", "formula", "setup", "rule", ...]`.
- `GET /api/knowledge/statuses` — Vocabulary: `["draft", "needs_testing", "trusted", "rejected", "archived"]`.
- `GET /api/knowledge/cards` — List. Query filters: `kind`, `status`, `strategy_id`, `tag`, `q` (text search across name/summary/body).
- `GET /api/knowledge/cards/{card_id}` — Single card.
- `POST /api/knowledge/cards` — Create. Required: `kind`, `name`, `status`. Optional: `summary`, `body`, `formula`, `inputs`, `use_cases`, `failure_modes`, `strategy_id`, `linked_run_id`, `linked_version_id`, `linked_research_entry_id`, `tags`.
- `PATCH /api/knowledge/cards/{card_id}` — Edit any field. Re-validates evidence links if strategy/link fields change. 422 if links violate strategy scoping.
- `DELETE /api/knowledge/cards/{card_id}` — Removes card; gently clears it from any research entry's `knowledge_card_ids` list.

**Schema:** `KnowledgeCardRead` includes `id`, `kind`, `name`, `summary`, `body`, `formula`, `inputs[]`, `use_cases[]`, `failure_modes[]`, `status`, `strategy_id`, `linked_run_id`, `linked_version_id`, `linked_research_entry_id`, `tags[]`, `created_at`, `updated_at`.

**Gotchas:**

- Evidence link FKs are validated on create + update: target must exist; if card is strategy-scoped, link target must belong to same strategy.
- Global cards (`strategy_id=null`) can link to evidence from any strategy.
- DELETE is a hard delete, not archive — the card disappears immediately.

### Research (`backend/app/api/research.py`)

Per-strategy research entries (hypothesis / decision / question), plus a one-shot promote-to-knowledge-card workflow.

- `GET /api/strategies/{strategy_id}/research` — List entries for a strategy. Filters: `kind` (hypothesis|decision|question), `status` (open|running|confirmed|rejected|done — valid set depends on kind).
- `GET /api/strategies/{strategy_id}/research/{entry_id}` — Single entry.
- `POST /api/strategies/{strategy_id}/research` — Create. Required: `kind`, `title`, `body`, `status`. Optional: `linked_run_id`, `linked_version_id`, `knowledge_card_ids[]`, `tags`.
- `PATCH /api/strategies/{strategy_id}/research/{entry_id}` — Update. Re-validates kind/status combo and evidence links independently of each other.
- `DELETE /api/strategies/{strategy_id}/research/{entry_id}` — Removes entry; clears `linked_research_entry_id` from any knowledge card pointing at it.
- `POST /api/strategies/{strategy_id}/research/{entry_id}/promote` — Create a knowledge card derived from this entry. Body can override `kind`, `name`, `body`, `tags`, `summary`, `formula`, `strategy_id`. Default status derived from entry kind/status pair. Appends new card.id to entry.knowledge_card_ids. Idempotent — re-promote produces a second linked card; UI should confirm before re-promoting.
- `POST /api/strategies/{strategy_id}/research/{entry_id}/experiment` — Create an experiment from this entry. Binds entry → experiment.

**Schema:** `ResearchEntryRead` includes `id`, `strategy_id`, `kind`, `status`, `title`, `body`, `linked_run_id`, `linked_version_id`, `knowledge_card_ids[]`, `tags`, `created_at`, `updated_at`.

**Gotchas:**

- Kind/status pairs are validated. Some combos forbidden (e.g. `hypothesis` cannot be `done`; `decision` cannot be `running`). The validator runs on both create and PATCH.
- Promote is idempotent. UI should show a confirm dialog before second POST.
- Evidence link validation runs per strategy scoping on every operation.

### AI Context (`backend/app/api/ai_context.py`)

One read-only endpoint that returns a previewable bundle of the local memory the prompt generator would assemble for a given strategy.

- `GET /api/strategies/{strategy_id}/ai-context` — Returns recent research entries + relevant knowledge cards, capped at a configured max length, with token-count estimate.

**Schema:** `AiContextPreviewRead` includes `strategy_id`, `research_entries[]`, `knowledge_cards[]`, `estimated_tokens`, `truncated`.

**Gotchas:**

- Read-only. To change what's bundled, edit the strategy's research / knowledge cards directly.
- The bundle is what `POST /api/prompts/generate` would inline into the prompt body — preview before generating.

### Chat (`backend/app/api/chat.py`)

Per-strategy chat thread persisted to local SQLite. Used by the in-app chat panel to record conversations with Claude / Codex CLI from outside the app.

- `GET /api/strategies/{strategy_id}/chat` — List the thread (turns ordered chronologically).
- `POST /api/strategies/{strategy_id}/chat` — Append a turn (body: `role`, `content`).

**Schema:** `ChatTurnResponse` includes `id`, `strategy_id`, `role` (`"user" | "assistant"`), `content`, `created_at`.

**Gotchas:**

- Backend does not call any LLM. The chat is a transcript log; the user runs prompts externally and pastes responses back via POST.
- No streaming. POST is synchronous and returns the persisted turn.

### Features (`backend/app/api/features.py`)

Feature library used by the visual strategy builder. Each feature has a typed param schema so the builder can render input controls without hardcoding.

- `GET /api/features` — List all features in the registry.

**Schema:** Each feature: `id`, `name`, `category`, `description`, `param_schema` (JSON-schema-shaped input definitions), `inputs[]`, `outputs[]`.

**Gotchas:**

- Read-only registry. The set of features is hand-maintained in `FEATURES`.
- The visual builder persists the assembled spec to a strategy version's `spec_json` field via `PATCH /api/strategy-versions/{id}`. The features endpoint is just metadata for rendering the builder UI.
