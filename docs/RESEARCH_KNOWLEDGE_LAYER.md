# Research Knowledge Layer

> **Doc-only design.** No code, no schema changes, no migrations. This
> document maps the proposed research-knowledge taxonomy onto existing
> BacktestStation structures, identifies one genuine gap (Research
> Event Store), and recommends the smallest-next-patch.
>
> Cross-links: [`docs/ARCHITECTURE.md`](ARCHITECTURE.md),
> [`docs/ROADMAP.md`](ROADMAP.md), [`docs/AI_ROADMAP.md`](AI_ROADMAP.md).

## Mental model

```
Concept → Detector → Research Event → Study/Experiment → Decision → Strategy
```

- **Concept** — a broad market idea humans understand (SMT, PSP, CVD divergence, FVG, displacement, liquidity sweep, volume profile, opening range).
- **Detector** — code/rule that detects a measurable version of one concept.
- **Research Event** — one occurrence found in market data (per-bar observation: "NQ took prev 30m high at 9:37 while ES/YM did not").
- **Study/Experiment** — analysis of events, detectors, concepts, or strategies.
- **Decision** — human conclusion from research.
- **Strategy** — tradable rule combination, later.

## Reality report

| Entity | Existing mapping | Status | Recommendation |
|---|---|---|---|
| **Concept** | `KnowledgeCard` (`backend/app/db/models.py:605-652`), `kind=market_concept`. API: `app/api/knowledge.py`. UI: `frontend/app/library/page.tsx`. | **existing** | Do not duplicate. Use existing rows. Optional: add `linked_feature_names: list[str]` JSON column to surface concept→detector links. |
| **Detector** | `FEATURES` registry (`backend/app/features/__init__.py`). 10 primitives, role-tagged (`setup`/`trigger`/`filter`). API: `app/api/features.py`. | **existing** | Do not duplicate. Optional: add `knowledge_card_id: int \| None` to `FeatureSpec` for the inverse link. |
| **Research Event** | Closest neighbors: `LiveSignal` (`models.py:209` — trade-decision-shaped), `LiveSignalLog` (`production/live_signal_log.py` — trade-signal-shaped), `Trade` (`models.py:133` — filled trades), labeled outcomes parquet (`D:\data\research\labeled_outcomes\trades_v1.parquet` — outcome-only). None capture **non-trade per-bar observations**. | **MISSING — genuine gap** | Build new `research_events` store. Reuse JSONL writer pattern from `live_signal_log.py` (idempotent, hashed event_id, append-only). Per-detector files. |
| **Study/Experiment** | `Experiment` (`models.py:271-304`). Required FK to `StrategyVersion`. Decision enum: `pending \| promote \| reject \| retest \| forward_test \| archive`. API: `app/api/experiments.py`. | **partial** | Do not duplicate. To support studies of concepts/detectors/research events (not strategy versions), extend with optional `target_type` + `target_id` columns; make `strategy_version_id` nullable. Tracked as a follow-up patch, not part of the gap fix. |
| **Decision** | Three existing landings: `ResearchEntry` (`models.py:553`, `kind=decision`, per-strategy), `Note` (`models.py:351`, `note_type=decision`, general), `Experiment.decision` (per-experiment outcome). | **existing** | Do not duplicate. Per-concept decisions → `Note` with `note_type=decision`. Per-strategy → `ResearchEntry`. Per-A/B → `Experiment.decision`. |
| **Strategy** | `Strategy` + `StrategyVersion` + composable plugin (`backend/app/strategies/composable/`). Versions hold `spec_json` referencing FEATURES by name. API: `app/api/strategies.py`. UI: `frontend/app/strategies/[id]/build/`. | **existing** | Do not duplicate. Linkage to concepts is **derivable, not stored** — a strategy's spec lists features → each feature has a concept → transitive concept→strategy mapping. No new fields needed for v1. |

Inventory citations are exact paths/lines as of HEAD on 2026-05-08.

## Per-entity detail + "do not duplicate" rationale

### Concept → KnowledgeCard

`KnowledgeCard` already covers the use case. Existing fields:

```python
kind:    market_concept | orderflow_formula | indicator_formula |
         setup_archetype | research_playbook | risk_rule |
         execution_concept
status:  draft | needs_testing | trusted | rejected | archived
fields:  name, summary, body, formula, inputs, use_cases,
         failure_modes, source, tags, linked_run_id,
         linked_version_id, linked_research_entry_id, strategy_id
```

**Do not duplicate.** Creating a parallel `concepts` table with status `idea | active_research | validated | deprecated` introduces two competing status systems for the same conceptual object. Use `kind=market_concept` for SMT / PSP / FVG / etc.

**Optional small extension** (deferred until needed): a `linked_feature_names: list[str] | None` JSON column to express concept→detector links explicitly. Not required for v1.

### Detector → FEATURES registry

`backend/app/features/__init__.py` already defines:

```python
@dataclass
class FeatureSpec:
    fn: FeatureFn
    label: str
    description: str
    param_schema: dict[str, Any]
    roles: tuple[FeatureRole, ...]   # setup | trigger | filter
```

10 features registered: `co_score`, `decisive_close`, `fvg_touch_recent`, `orderblock_engulf`, `prior_level_sweep`, `smt_at_level`, `swing_sweep`, `time_window`, `volatility_regime`, `volume_profile`.

The composable plugin (`backend/app/strategies/composable/strategy.py`) consumes these by name from a strategy's `spec_json`.

**Do not duplicate.** A "research feature registry" with new role taxonomy (`detector | context | filter | trigger | entry | risk | outcome`) creates two competing role systems. The existing `setup | trigger | filter` is the single source of truth.

**Optional small extension** (deferred): a `knowledge_card_id: int | None` field on `FeatureSpec` for the inverse link from detector→concept. Not required for v1 — naming-by-convention works (e.g. `smt_at_level` → KnowledgeCard with `name="SMT"`).

### Research Event → MISSING (genuine gap)

This is the only entity not covered by an existing structure.

**Why existing structures don't fit:**

| Structure | Why it doesn't fit |
|---|---|
| `LiveSignal` (DB table) | Trade-decision-shaped: `side`, `price`, `executed: bool`. No event_data, no outcomes, no detector_version. Captures "we saw a tradable signal," not "we saw a pattern." |
| `LiveSignalLog` (JSONL via `production/live_signal_log.py`) | Closer — has `feature_snapshot` and replay context — but the universal envelope is trade-signal-shaped: `ref_price`, `stop_price`, `target_price`, `contracts`, `risk_snapshot`, `execution_snapshot`. Generalizing it to a non-trading research event would require gutting the trading-specific block. |
| `Trade` | Post-fill trades. Backward-looking. Doesn't capture pre-trade observations or non-traded patterns. |
| `labeled_outcomes` parquet | Per-trade outcome rows. Same problem — trades only, not generic detections. |
| `BacktestRun` + `Trade` | A backtest run is a *strategy* run that produced *trades*, not a detector pass that produced *observations*. |
| `ResearchEntry`, `Note` | Markdown-bodied human entries. Not structured event records. |

**A research event is per-detector, not per-strategy.** A single 1m bar might fire 5 detectors (SMT, sweep, FVG, displacement, decisive_close); none of them are strategies. None should land as a `LiveSignal` row. Volume is also 100×+ higher than live signals, since most events do not become trades.

### Study/Experiment → existing `Experiment` (partial fit)

`Experiment` (lines 271-304) covers strategy-version A/B testing. Its required FK to `StrategyVersion` makes it unsuitable for concept-level or detector-level studies without modification.

**Recommendation, deferred (not part of this patch):** make `strategy_version_id` nullable and add optional `target_type` (`concept | detector | research_event | strategy_version`) + `target_id` columns. Keep the existing decision enum.

Until then, concept/detector studies can land as `Note` rows with `note_type=hypothesis`/`observation`/`decision` and `tags=["smt-study", ...]`. Less structured but doesn't require schema work.

### Decision → existing landings

Three landings already cover the use case:

- **Per-concept decision**: `Note` with `note_type=decision`. General scope (no strategy required).
- **Per-strategy decision**: `ResearchEntry` with `kind=decision`. Markdown body, FK to `strategy_id`.
- **Per-A/B-test outcome**: `Experiment.decision` field.
- **Per-promotion-candidate**: `StrategyPromotionCheck.status` (separate concern — full robustness verdict aggregating all evidence).

**Do not duplicate.** No new Decision table.

### Strategy → existing `Strategy` + `StrategyVersion`

The composable plugin reads `spec_json` from `StrategyVersion`. Each spec lists features by name. Each feature optionally maps to a concept (via the optional extension above).

**Linkage direction**: derive concept→strategy from the feature membership of each version's spec, not from a stored `Strategy.concept_ids` list. A strategy's concepts change with its spec; a denormalized list would drift.

The inverse — KnowledgeCard.related_strategy_ids — is also not needed if it's derivable. Only add it if read-time derivation proves slow at scale.

## Genuine gap analysis

Exactly one gap: the **Research Event Store**.

The other five entities map cleanly onto existing structures, with two small optional extensions if/when needed (`KnowledgeCard.linked_feature_names`, `FeatureSpec.knowledge_card_id`). Both are deferrable.

## Proposed Research Event Store (PROPOSED ONLY)

Reduced from the 16-field draft. Inventory shows fields that overlap with existing tables; we keep only what's genuinely new.

```python
class ResearchEvent(Base):
    __tablename__ = "research_events"

    id: int                          # surrogate
    event_id: str                    # stable hash, idempotent insert key
    feature_name: str                # FK by-string to FEATURES registry
    knowledge_card_id: int | None    # FK to knowledge_cards (concept)
    event_type: str                  # detector-defined: "smt_high",
                                     # "fvg_creation", "sweep_pdh", etc.
    bar_end_utc: datetime            # canonical timestamp
    primary_symbol: str
    symbols: list[str]               # all symbols involved
    timeframe: str                   # "1m", "5m", "30m", "1h"
    side: str | None                 # "bullish" | "bearish" | "high"
                                     # | "low" | None
    event_data: dict                 # detector-specific decision context
    context: dict                    # session, regime, vol, news flags
    outcomes: dict                   # forward-window observations
    replay_pointer: dict | None      # {run_id, dataset, ts_range}
    source_dataset: str | None       # parquet/dbn path
    source_run_id: int | None        # FK to backtest_runs (if event was
                                     # generated during a run)
    detector_version: str | None
    created_at: datetime
```

**Fields dropped from the draft**:

- `concept_id` collapsed into `knowledge_card_id` (single FK, not two competing keys).
- `detector_id` collapsed into `feature_name` (string ref to FEATURES registry; FEATURES doesn't have integer ids).
- `direction` merged into `side` (one field, documented values).

**Storage decision**: **DB table, not JSONL.** Differs from `LiveSignalLog`:

| Concern | LiveSignalLog (JSONL) | ResearchEvent (DB table) |
|---|---|---|
| Volume | One row per trade signal — low | One row per detector hit — high (100×+) |
| Query patterns | Append-only, sequential read | Filtered by detector × symbol × date range |
| Writer | Live trading bot (latency-sensitive) | Detector replay/scan jobs (batch) |
| Concurrent writers | One per strategy | Many parallel detector runs |

DB tables index well on `(feature_name, bar_end_utc, primary_symbol)` for the typical query "all SMT events on NQ in the last 30 days." JSONL doesn't.

**ID hashing pattern**, reused from `live_signal_log.py:make_signal_id`:

```python
def make_event_id(feature_name, primary_symbol, bar_end_utc, event_type) -> str:
    raw = f"{feature_name}|{primary_symbol}|{bar_end_utc.isoformat()}|{event_type}"
    return f"{feature_name}-{blake2b(raw, 8).hexdigest()}"
```

Idempotent insert: skip if `event_id` already exists.

## How SMT v1 uses the system

```
Concept:     KnowledgeCard(kind="market_concept", name="SMT",
                           summary="Smart Money Technique — divergent
                                    high/low takes between correlated
                                    futures (NQ vs ES vs YM)")

Detector:    FeatureSpec("smt_at_level", roles=("setup", "filter"),
                        param_schema={...})
             # Already exists in FEATURES registry today.

Detector v2: FeatureSpec("smt_prev_candle_divergence",
                        roles=("setup",))
             # New detector module to add later. Same registry.

Research
events:      ResearchEvent rows, one per NQ/ES/YM divergence detection.
             event_type = "smt_high" or "smt_low"
             event_data = {first_break_symbol, lagging_symbols,
                           reference_mode: "prev_candle_high",
                           reference_high_nq, reference_high_es,
                           reference_high_ym, confirm_ts_*}
             context = {session: "NY_AM", vol_regime: "high",
                        news_within: false}
             outcomes = {fwd_5m_mfe_pts, fwd_15m_mfe_pts,
                         fwd_30m_mfe_pts, fwd_60m_mfe_pts,
                         fwd_5m_mae_pts, ...}

Study:       Experiment row (after the schema extension lands)
             OR Note(note_type=hypothesis, body="30m prev-candle SMT
             between 9:30 and 10:00 ET — does NQ-led high-side SMT
             produce >0.5R median MFE within 30m?")

Decision:    Note(note_type=decision, body="Promoted to feature: ...")
             OR ResearchEntry(kind=decision, ...) once the work is
             scoped to a specific strategy.

Strategy:    Composable spec. SMT + PSP + CSD reversal — listed by
             feature name in StrategyVersion.spec_json. The
             concept→strategy mapping is derivable from spec membership.
```

**No new SMT detector code is implied by this doc.** The `smt_at_level` feature already exists. Adding `smt_prev_candle_divergence` is a separate, scoped patch that lives in `backend/app/features/` and tests in `backend/tests/`.

## Obsidian integration

**BacktestStation is the source of truth.** Concepts, detectors, research events, studies, decisions, results all live in the DB or in `D:\data\`.

**Obsidian is export-only — a human-readable knowledge graph.** A future export utility can render selected KnowledgeCard / Experiment / ResearchEvent rows as markdown files with backlinks. None of that exists yet.

**Do not add `obsidian_path` fields to any model until the export utility is built.** Premature column. If/when the exporter exists, it derives Obsidian filenames from the canonical row id, no extra column needed.

## Smallest next patch

**One paragraph, ranked by reversibility (least reversible first):**

Build the `research_events` table + `make_event_id` helper + a single `GET /api/research/events` endpoint with `(feature_name, primary_symbol, bar_end_utc range)` filters. Add a migration via the same pattern in `app/db/session.py:_run_data_migrations`. Add `app/services/research_events.py` with `record_event(...)` for write-side use by future detector scan jobs (no detectors written in this patch). Add `tests/test_research_events.py` covering insert idempotence + filter query. Defer the frontend page, the `Experiment` schema extension, the optional `KnowledgeCard.linked_feature_names` column, and any new SMT detector logic to follow-up patches. **Estimated scope: ~150 LOC backend + ~80 LOC tests, no UI, no live trading impact.**

## Acceptance check

- [x] No code outside this doc.
- [x] Reality-report table covers all six entities with exact file paths and route names (`models.py:605`, `app/api/knowledge.py`, etc).
- [x] For each entity that maps to existing structures, "do not duplicate" stated explicitly.
- [x] For the one genuine gap (Research Event), why existing structures can't absorb it is explained with a per-structure breakdown.
- [x] Research Event vs LiveSignalLog answered explicitly (separate store, not generalization — different volume, query patterns, writers).
- [x] Smallest-next-patch is one paragraph, ranked by reversibility.
- [x] Doc under 600 lines.
- [x] Cross-linked from `docs/ARCHITECTURE.md` and `docs/ROADMAP.md`.
