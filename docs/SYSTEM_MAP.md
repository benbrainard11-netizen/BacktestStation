# SYSTEM_MAP — what is in this project, where it lives, and its status

_Single source of truth for the BacktestStation workspace as of 2026-05-17. Replaces scattered tribal knowledge._

When in doubt about whether something is current, look here. When you find drift between this file and reality, fix this file or fix reality.

## Status taxonomy

Every item has one status:

| Status | Meaning |
|---|---|
| **core** | Load-bearing, must be present, changes need extreme care |
| **active** | Currently being used; safe to modify with normal care |
| **reference** | Historical context; not changing but kept for understanding |
| **deprecated** | Replaced by newer thing; will be archived next sweep |
| **archived** | Moved to `experiments/archive/` or similar; out of active workspace |
| **unknown** | Not yet classified; default for anything not in this map |

Full definitions: `docs/STATUS_TAXONOMY.md`.

## Repository layout (current)

### `backend/` — the Python codebase

| Path | Status | What |
|---|---|---|
| `backend/app/db/models.py` | **core** | SQLAlchemy models. Recently added trial registry plus dataset snapshot provenance tables. |
| `backend/app/db/session.py` | **core** | DB engine + `_run_data_migrations()`. ALL migrations go here for now (Alembic deferred). |
| `backend/app/engine/` | **core** | Pure backtest engine. No imports from api/db/storage/ingest per CLAUDE.md rule #1. |
| `backend/app/research/detectors/` | **core** | The 14+ event detectors (FVG, OB, sweep, swing, etc.). Code-reviewed FVG + 22 tests pass. |
| `backend/app/research/outcomes/` | **core** | Outcome computers (reaction labels). Includes the level-reactions schema from 247. |
| `backend/app/ingest/` | **active** | R2 + Databento ingestion. Has known inventory-overwrite bug (prompt sent to 247). |
| `backend/scripts/ml/rigorous_backtest_v1.py` ... `v9_ob.py` | **core** | The v8a simulator stack. **FROZEN per validation-lockdown until v21 protocol completes.** |
| `backend/scripts/ml/v13_registry_audit.py` | **reference** | The audit that found Type B clusters. Already executed; results in archive. |
| `backend/scripts/ml/v15-v19_*.py` | **reference** | Slippage / sanity / TBBO / strict-label checks from this weekend's validation chain. Executed. |
| `backend/scripts/ml/v20_locked_walkforward.py` | **reference** | The locked walk-forward executor. Completed; result is PARTIAL FAIL. |
| `backend/scripts/ml/tbbo_resolver.py` | **active** | Reusable TBBO honest-fill resolver. Should be kept for v21. |
| `backend/scripts/ml/v14_*.py` | **deprecated** | level-reactions audit attempt — null result, waiting on `reaction.fire_ts` schema from 247. |
| `backend/tests/test_trial_registry.py` | **core** | Trial registry tests (3, all pass). |
| `backend/tests/test_dataset_snapshots.py` | **core** | Dataset snapshot schema/provenance tests. |
| `backend/tests/test_liquidity_sweep_reactions.py::test_ob_confirmation_join` | **unknown** | KNOWN pre-existing failure in full suite. Needs investigation (247 lane). |

### `data/` — local data (gitignored)

| Path | Status | What |
|---|---|---|
| `data/meta.sqlite` | **core** | 37 GB metadata DB. Strategies, runs, trades, datasets, research events, trial registry. |
| `data/research_events/` | **core** | 4.22M events / 176 parquets across 15 features. Manifest hash anchors snapshots. |
| `data/ml/features/` | **core** | 14 per-detector feature matrices. Plus `eql.parquet` (built from swing). |
| `data/ml/levels/` | **active** | 6-family level-reactions + combined `all_level_reactions.parquet`. From 247's recent work. |
| `data/ml/catalog/` | **active** | Asset universe manifest, ML dataset catalog, warehouse inventory, label registry. |
| `data/ml/logs/` | **active** | R2 publish run summaries. |

### `experiments/`

| Path | Status | What |
|---|---|---|
| `experiments/locked_walkforward_2026_05_17/` | **active** | The v20 lockfile + pre-registration + results. Lock status: completed. |
| `experiments/backtests/2026-05-17_*` | **active** | Today's v14-v19 audit results. |
| `experiments/archive/` | **archived** | 31 older experiment dirs from May 15-16. Out of active workspace. |
| `experiments/gpu_runs/` | **archived** | Per .gitignore note: "earlier experiments layout, retired." |

### `D:/` — external data root

| Path | Status | What |
|---|---|---|
| `D:/data/raw/databento/` | **core** | Immutable raw DBN files. Append-only per CLAUDE.md rule #7. |
| `D:/data/processed/bars/timeframe=1m/` | **core** | Derived 1m bars (parquet). 2015-01-01 to 2026-05-15, 11 years, 28 symbols. |
| `D:/data/processed/bars/timeframe=tbbo/` | **core** | TBBO data. 2025-05 to 2026-05 only (1 year). |
| `D:/data/manifests/ingest_runs/` | **core** | 28 ingest manifests with sha256 hashes per file. |
| `D:/BacktestStationData/strategy_lab_core_*` | **active** | Anchor matrix release zips from 247. Have years 2015-2026. |

### R2 bucket `bsdata-prod`

| Prefix | Status | What |
|---|---|---|
| `_root_` files | **core** | `_inventory.json` (May 6, stale for raw bars), `_research_inventory.json` (current) |
| `data/ml/` | **core** | Research artifacts. ~7 GB. Republished today (v9+ handoffs). |
| `data/research_events/` | **core** | Parquet export of research events. ~2 GB. |
| `data/ml/levels/` | **active** | Level-reactions parquets (6 families + combined). |
| `exports/` | **active** | Strategy lab release zips. ~9 GB. |
| `processed/bars/` | **core** | 1m bars mirror. ~1.2 GB. |
| `raw/` | **core** | Raw DBN mirror. ~21 GB. |

### `docs/` — documentation

**Core (do not let drift):**
- `CLAUDE.md` (repo root) — engineering rules
- `docs/ARCHITECTURE.md` — system design
- `docs/ROADMAP.md` — direction
- `docs/SCHEMA_SPEC.md` — warehouse schemas
- `docs/STATUS_TAXONOMY.md` — taxonomy rules
- `docs/SYSTEM_MAP.md` — this file
- `docs/OPERATING_RULES.md` — the 5 non-negotiables
- `docs/CANDIDATE_LIFECYCLE.md` — strategy candidate state machine
- `docs/TABLE_REGISTRY.md` — every DB table classified

**Active (recent, in use):**
- `docs/TYPE_B_DEPLOY_CANDIDATE_2026_05_17.md` — current deploy candidate writeup
- `docs/TRIAL_REGISTRY_USAGE.md` — how to use the new trial tables (from 247)
- `docs/DATASET_SNAPSHOT_USAGE.md` - how to create/query snapshot provenance rows
- `docs/BEN_247_PROMPT_2026_05_17_*.md` (4 files) — open 247 asks
- `docs/RESEARCH_VALIDATION_PACKET_2026_05_17.md` — evidence packet for external review
- `docs/TBBO_RESOLVER_DESIGN_2026_05_17.md` — TBBO design notes

**Reference (don't update routinely):**
- `docs/TYPE_B_DEPLOY_CANDIDATE_2026_05_16.md` — superseded by 05_17 version
- `docs/OVERNIGHT_2026_05_16_*.md` — historical session briefings
- `docs/ML_TYPE_B_DISCOVERY_2026_05_16.md` — original Type B finding
- `docs/BEN_247_PROMPT_2026_05_16_*.md` — pre-validation-lockdown ask

**Unknown/needs review:**
- Other older docs in `docs/` not classified above. Inventory pass needed.

### `scripts/` — top-level utility scripts

| Path | Status | What |
|---|---|---|
| `scripts/check_doc_drift.py` | **active** | Catches test-count drift between README and reality. |
| `scripts/build_audit_bundle.py` | **active** | Assembles R2 audit bundle + presigned URL for external review. |
| `scripts/data_inventory_report.py` | **active** | Factual partition inventory (counts/sizes/hashes/year coverage). Not semantic validation. |
| `scripts/install_*.ps1` | **reference** | Scheduled-task installers. |
| `scripts/mirror_to_husky.ps1` | **reference** | Collaborator data mirroring. |

### `backend/scripts/data/` — backend data utilities

| Path | Status | What |
|---|---|---|
| `backend/scripts/data/create_snapshot.py` | **active** (skeleton) | Creates dataset snapshots. DB schema is now present on the Q1 branch; benpc owns wiring the utility to write snapshot rows. |

## Current deploy candidate

**Status**: paper-trade candidate (NOT real-money deployable yet)

```
candidate: OB strict + Sweep reversed (filtered)
v20 locked walk-forward result: 2-family core passed; 4-family failed
expected per-year R: 250-350R (base case) / 100-200R (conservative)
expected per-year $ return on $150K capital: 25-80% (triangulated by 3 reviewers)
killed: Swing reversed (regime artifact, direction-flip falsifier hit)
research-only: FVG strict (regime-dependent, not deploy-core)
```

Next gates required before paper trade:
1. Roll-anomaly check (limited — no per-contract bars on disk)
2. Day/week block bootstrap
3. Fill-model torture (target-through + volume-gating)
4. Single-account portfolio simulator
5. v21 lockfile (the 2-family core, freshly locked)

## Open coordination items

| Item | Owner | Status |
|---|---|---|
| Dataset snapshots schema build | 247 | Q1 branch shipped (`dataset-snapshots-v2`) |
| Trial registry merged to active branch | benpc | Done (`d910324`) |
| `reaction.fire_ts` on level-reactions | 247 | Prompt sent (older) |
| R2 inventory-overwrite bug fix | 247 | Prompt sent (older, has ready-to-apply Python) |
| Pre-existing test failure (sweep reactions ob_confirmation_join) | 247 | Flagged but not in queue yet |

## Honest gaps (what this map doesn't cover yet)

- `backend/app/api/`, `backend/app/cli/` — not classified yet, needs a pass
- `frontend/` — UI work not in active scope; defer until deploy decision
- `shared/openapi.json`, `frontend/lib/api/generated.ts` — type generation pipeline, see CLAUDE.md rule #4
- Some `docs/ML_*` files from earlier weeks — not yet status-tagged

## Maintenance

This file should be updated when:
- A new major component lands
- An item changes status (active → archived, etc.)
- A new directory is added at the repo root
- A reviewer's question reveals drift

Don't update it for routine code edits.
