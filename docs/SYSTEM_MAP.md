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
| `backend/app/db/models.py` | **core** | SQLAlchemy models. Recently added trial registry, dataset snapshots, and validation report tables. |
| `backend/app/db/session.py` | **core** | DB engine + `_run_data_migrations()`. ALL migrations go here for now (Alembic deferred). |
| `backend/app/engine/` | **core** | Pure backtest engine. No imports from api/db/storage/ingest per CLAUDE.md rule #1. |
| `backend/app/research/detectors/` | **core** | The 14+ event detectors (FVG, OB, sweep, swing, etc.). Code-reviewed FVG + 22 tests pass. |
| `backend/app/research/outcomes/` | **core** | Outcome computers (reaction labels). Includes the level-reactions schema from 247. |
| `backend/app/research/validation/` | **core** | Semantic gate framework + 48 gates across 4 schemas + `runner.py` (walks snapshot, writes report+findings to DB). 71 tests pass. End-to-end smoke verified against real warehouse. See `docs/VALIDATION_DESIGN.md`. |
| `backend/app/api/dashboard/` | **active** | Operator dashboard API namespace. Data Health backend endpoints for R2 status, local coverage, latest validation, and validation findings. |
| `backend/scripts/data/create_snapshot.py` | **active** | Builds + persists a `dataset_snapshots` row (wired to 247's Q1 schema). Computes per-partition sha256, manifest hash, deterministic snapshot_id. |
| `backend/scripts/data/validate_snapshot.py` | **active** | CLI that runs the validation runner against a snapshot_id. Writes `partition_validation_reports` + `partition_validation_findings`. Wrapped by `bs data validate` (Q3). |
| `backend/app/ingest/` | **active** | R2 + Databento ingestion. Has known inventory-overwrite bug (prompt sent to 247). |
| `backend/scripts/cli/` | **active** | `bs` operator CLI: doctor / status / data / snapshot / trial v1 commands (Q3). |
| `backend/scripts/data/` | **active** | Snapshot + validation entry points: `create_snapshot.py`, `validate_snapshot.py`, `smoke_validate_partitions.py`. |
| `backend/scripts/ml/rigorous_backtest_v1.py` ... `v9_ob.py` | **core** | The v8a simulator stack. **FROZEN until v21 protocol completes.** Trade rule, fill model, stop/target sim live here. |
| `backend/scripts/ml/v13-v20_*.py` | **reference** | Validation chain (May 2026): registry audit (v13), slippage/sanity/TBBO checks (v15-v19), locked walk-forward (v20, PARTIAL FAIL). |
| `backend/scripts/ml/v22-v29_*.py` | **reference** | Post-v20 research: 4 paper-trade gates (v22-v25), concurrency diagnosis (v26), expanded-universe walk-forwards (v27-v28), per-symbol analysis (v29). See `experiments/paper_trade_gates_2026_05_17/` and `experiments/fresh_holdout_2015_2017/`. |
| `backend/scripts/ml/v30_feature_profiles.py` | **active** | Per-feature × per-asset behavior profiler. Reads all events + outcomes, writes profile CSVs + SUMMARY. See `experiments/feature_profiles_*/`. |
| `backend/scripts/ml/tbbo_resolver.py` | **active** | Reusable TBBO honest-fill resolver. Lives here for v21 reuse. |
| `backend/scripts/ml/v14_*.py` | **deprecated** | level-reactions audit — null result; waiting on `reaction.fire_ts` from 247. |
| `backend/scripts/generate_events_2015_2017.py` | **active** | Run detectors over 2015-2017 bars; writes events to DB (idempotent). |
| `backend/scripts/build_slim_anchors_2015_2017.py` | **active** | Build "slim" anchor parquet from research events + recomputed strict label. Symbol-configurable. |
| `backend/scripts/export_research_events_to_parquet.py` | **active** | Re-export research_events from DB to partitioned parquets when the DB has rows the parquet mirror is missing. |
| `backend/scripts/overnight_queue.py` | **active** | Sequential subprocess runner for long overnight DB additions + analyses + cleanups. Kill-tree hardened on Windows. |
| `backend/tests/test_trial_registry.py` + `test_dataset_snapshots.py` + `test_validation_reports.py` + `test_validation_runner.py` + `test_validation_gates.py` + `test_cli.py` + `test_dashboard_data_health.py` | **core** | Schema + registry + CLI + dashboard test suites. ~100 tests across the foundation. |
| `backend/tests/test_liquidity_sweep_reactions.py::test_ob_confirmation_join` | **unknown** | Pre-existing failure in full suite. Needs investigation (247 lane). |

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

## Current deploy candidate

**Status**: paper-trade candidate (NOT real-money deployable yet)

```
candidate: OB strict + Sweep reversed (filtered)
v20 locked walk-forward result: 2-family core passed; 4-family failed
v28 fresh 2015-2017 holdout: ~1,735 R/yr (consistent within 6% of 2018-2019)
v25 single-account haircut: ~53% retention -> ~590-940 R/yr at cap=2
expected per-year R live (planning bar): 300-600 R/yr
killed: Swing reversed (regime artifact -- but unreversed shows 65% hit rate; worth re-test)
research-only: FVG strict (regime-dependent, not deploy-core)
```

Next gates required before paper trade:
1. Roll-anomaly check (v22) ✓ PASS
2. Day/week block bootstrap (v23) ✓ PASS
3. Fill-model torture (v24) ✓ PASS
4. Single-account portfolio simulator (v25) ✗ FAIL (retention 53% vs 70% threshold; diagnosed in v26, partially mitigated by v27/v28)
5. v21 lockfile (the 2-family core, freshly locked) — pending
6. Paper-trade infrastructure (live signal generator + drift report) — pending 247 Q8

## Open coordination items

| Item | Owner | Status |
|---|---|---|
| 247 execution queue Q1-Q5 | 247 | Done — all merged (`5fe75b7` Q1+Q2, `157aa0c` Q3, `bc07134` Q4, this commit Q5) |
| 247 execution queue Q6-Q8 (Trials/Candidates/Live Monitor) | 247 | Q6 merged; Q7 frontend in branch; Q8 queued |
| Validation library + runner + CLI wiring | benpc | Done (`39e5faf` + `157aa0c`) — 102 tests pass, end-to-end smoke verified |
| Trial registry | benpc | Done (`d910324`) |
| Full-warehouse validation report | benpc | Done — 64,843 partitions; only `missing_minutes` calibration warns/fails (now session-aware) + 14 RTY VWAP warnings to investigate |
| `reaction.fire_ts` on level-reactions | 247 | Prompt sent (older) |
| R2 inventory-overwrite bug fix | 247 | Prompt sent (older, has ready-to-apply Python) |
| Pre-existing test failure (sweep reactions `ob_confirmation_join`) | 247 | Flagged but not in queue yet |
| forming_volume_profile outcomes timeout | benpc | Re-running on B2 of cleanup pass (no timeout) |
| Stale research_events parquet (missing 2015-2017 events) | benpc | `export_research_events_to_parquet.py` written; run on demand |

## Honest gaps (what this map doesn't cover yet)

- `backend/app/api/`, `backend/app/cli/` — not classified yet, needs a pass
- `backend/app/api/dashboard/` - operator dashboard APIs; Data Health live, Trials/Candidates backend added in Q6
- `frontend/app/data-health/` - active dashboard Data Health screen; Q5 frontend build
- `frontend/app/trials/`, `frontend/app/candidates/` - Trials/Candidates operator screens; Q7 frontend build
- `shared/openapi.json`, `frontend/lib/api/generated.ts` — type generation pipeline, see CLAUDE.md rule #4
- Some `docs/ML_*` files from earlier weeks — not yet status-tagged

## Maintenance

This file should be updated when:
- A new major component lands
- An item changes status (active → archived, etc.)
- A new directory is added at the repo root
- A reviewer's question reveals drift

Don't update it for routine code edits.
