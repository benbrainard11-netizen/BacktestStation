# TABLE_REGISTRY — every table in `meta.sqlite`, classified

_As of 2026-05-17. Status definitions in `docs/STATUS_TAXONOMY.md`. Companion to `docs/SYSTEM_MAP.md`._

The metadata DB has accumulated tables over many sessions. This registry classifies each one. If a table isn't here, it's `unknown` and needs to be classified.

## Live tables (currently in `data/meta.sqlite`)

| Table | Status | Rows (snapshot) | Purpose |
|---|---|---:|---|
| `strategies` | core | 0 | Strategy catalog (parent for versions/runs) |
| `strategy_versions` | core | 0 | Versioned strategy logic + status (per CANDIDATE_LIFECYCLE) |
| `strategy_promotion_checks` | active | 0 | Recorded promotion checks per version |
| `backtest_runs` | core | 0 | Run header (one per backtest execution); needs `dataset_snapshot_id`, `code_commit_sha`, `seed` (247 in flight) |
| `trades` | core | 0 | Per-trade results from runs |
| `equity_points` | core | 0 | Equity curve samples |
| `run_metrics` | core | 0 | One-to-one summary metrics per run |
| `config_snapshots` | core | 0 | Run config payloads |
| `datasets` | core | 130,191 | File-inventory cache (R2 partitions, parquets). Not a "dataset snapshot" — that's coming separately. |
| `research_events` | core | 4,158,076 | The detector event surface — the most populated table by far |
| `experiments` | active | 0 | Hypothesis/baseline/variant ledger; partly redundant with new trial registry, will reconcile |
| `notes` | active | 0 | Research notes attachable to strategy/version/run/trade |
| `knowledge_cards` | active | 5 | Concept/detector/decision summaries |
| `research_entries` | active | 0 | Free-form research log entries |
| `risk_profiles` | active | 3 | Named risk-cap bundles |
| `firm_rule_profiles` | active | 11 | Prop-firm rule profiles |
| `prop_firm_simulations` | active | 0 | Persisted Monte Carlo sim outputs |
| `live_signals` | active | 0 | Live strategy signals |
| `live_heartbeats` | active | 0 | Live process health |
| `chat_messages` | unknown | 0 | TBD — possibly stale UI chat feature; needs classification |

## Tables shipped but not yet migrated into this DB

These tables exist in `backend/app/db/models.py` and `_run_data_migrations`, but `data/meta.sqlite` was last touched before they landed. They'll appear on next backend startup.

| Table | Status | Purpose | Source commit |
|---|---|---|---|
| `hypotheses` | active | Falsifiable research claims | `d910324` (trial registry) |
| `trial_groups` | active | Bounded search/audit groups under a hypothesis | `d910324` |
| `trials` | active | Individual trial runs with results | `d910324` |
| `trial_lock_records` | active | Multi-window lock chain (pre_validation / pre_test / final) | `d910324` |

## Tables coming soon (247 build in flight)

Per `docs/BEN_247_PROMPT_2026_05_17_DATASET_SNAPSHOTS.md`:

| Table | Status (planned) | Purpose |
|---|---|---|
| `dataset_snapshots` | core (after merge) | Immutable record of data state at a snapshot time |
| `dataset_snapshot_partitions` | core (after merge) | One row per partition included in a snapshot |
| `backtest_runs.dataset_snapshot_id` (NEW COLUMN) | core | Run-level provenance |
| `backtest_runs.code_commit_sha` (NEW COLUMN) | core | Run-level code identity |
| `backtest_runs.seed` (NEW COLUMN) | active | Reproducibility for randomized strategies |

## Tables on the wishlist (not yet asked for)

These would fit the operating spine but no prompt has been sent:

| Table (proposed) | Status (would be) | Purpose | Owner |
|---|---|---|---|
| `partition_validation_reports` | core | Partition-level integrity proofs (row count, hashes, gap counts, etc.) | 247 (future ask) |
| `strategy_status_transitions` | active | Audit log of candidate lifecycle changes | 247 (future ask) |
| `bug_exceptions` | active | Records bug-fix exceptions during locked tests | 247 (future ask) — currently JSON in `trial_lock_records.bug_exceptions_after_lock_json` |

## Status-of-content observations

**Most rows live in two tables:**
- `research_events`: 4.16M rows. The actual research data.
- `datasets`: 130K rows. File inventory.

**Everything else is sparse or empty.** The schema is overbuilt relative to actual records — common pattern when a project's pipelines outpace its discipline. The trial registry + dataset snapshots will start populating the empty tables going forward.

**Strategies / backtest_runs are empty.** This is because v8a / v13 / v15 / v16 / v17 / v20 results have been stored as CSV files in `experiments/` rather than persisted to `meta.sqlite`. Per `OPERATING_RULES.md` rule 2 ("every run belongs to a trial"), new runs going forward should populate the DB. Historical runs can be backfilled or grandfathered as exploratory.

## Reconciliation plan

Some tables are partly redundant:

| Possibly redundant | Old role | New role |
|---|---|---|
| `experiments` vs `trial_groups` | Pre-trial-registry concept | Old `experiments` table → `reference`; new `trial_groups` → `active` (migration pending) |
| `strategy_promotion_checks` vs `strategy_status_transitions` (wishlist) | Existing single-table notion | Wishlist would replace with proper audit log |

Reconciliation work is deferred until the operating spine is fully in place. Don't try to migrate `experiments` data into `trial_groups` retroactively without explicit planning.

## Maintenance

Update this file when:
- A new table lands in `models.py`
- A table changes status (active → core, etc.)
- A reconciliation between redundant tables completes
- A reviewer's question reveals drift

Don't update for routine row inserts or schema column tweaks unless the table's role changes.
