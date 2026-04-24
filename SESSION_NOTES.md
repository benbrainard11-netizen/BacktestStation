# Session notes — 2026-04-24

> Temporary doc. Delete once Ben + Husky review and decide what to merge.

This session ran while Ben was at the gym. Three branches stacked on top
of each other; nothing pushed, nothing merged, no PRs opened.

## Branch chain

```
main
└─ task/strategy-editor-pipeline
   ├─ commits added this session:
   │    f4cfdf3  Add archive-not-delete for strategy versions
   │    06af82b  Strategy dossier polish + board/table view toggle
   │    e08c391  Align ARCHITECTURE + CLAUDE.md with strategy workstation direction
   │
   └─ feat/research-workspace
      ├─ commits:
      │    659f5d1  Research Workspace: extend Note model + endpoints + vocabulary
      │    69d989f  Regenerate openapi.json + TS types for Note vocabulary endpoints
      │    7fb81be  Wire NotesPanel into strategy dossier
      │
      └─ feat/experiment-ledger
         └─ commits:
              d6adfe5  Experiment Ledger: backend model + endpoints + tests
              f80e7ff  ExperimentsPanel scaffold on strategy dossier
              b6f345b  Refresh PHASE_1_SCOPE + PROJECT_CONTEXT to point at the Workstation vision
```

Branch tip is `feat/experiment-ledger`. To inspect each layer:

```bash
git checkout task/strategy-editor-pipeline   # archive lifecycle + dossier polish + docs
git checkout feat/research-workspace          # adds: Notes panel
git checkout feat/experiment-ledger           # adds: Experiment ledger backend + scaffold UI
```

## What's on each branch

### `task/strategy-editor-pipeline` (continuing from earlier session)

Backend:
- `archived_at` column on `StrategyVersion` (idempotent ALTER migration)
- `DELETE /api/strategy-versions/{id}` returns 409 when runs attached
- `PATCH /api/strategy-versions/{id}/archive` and `.../unarchive`
- 4 new tests in `test_strategies_crud_api.py`

Frontend:
- Board ↔ table toggle on `/strategies`, persisted in `localStorage["bs.strategies.view"]`
- `StatusPill` stage chip on dossier
- `ArchiveStrategyButton` + per-version `ArchiveVersionButton`
- Latest-run metrics panel on dossier (reuses `MetricsGrid`)
- Research workspace placeholder (replaced in next branch)

Docs:
- `docs/ARCHITECTURE.md` §0 Vision + Scope + Current Phase + Next Phase + AI Direction + Safety + Build Order
- `CLAUDE.md` extended "What not to build yet" + new Schema migration discipline section

### `feat/research-workspace`

Backend:
- `Note` extended: `strategy_id`, `strategy_version_id`, `note_type`, `tags`, `updated_at` (idempotent ALTERs)
- `NOTE_TYPES` vocabulary: `observation, hypothesis, question, decision, bug, risk_note`
- `GET /api/notes/types`
- `POST /api/notes` accepts new fields, validates, normalizes tags
- `GET /api/notes` accepts `strategy_id`, `strategy_version_id`, `note_type`, `tag` filters
- `PATCH /api/notes/{id}` (sets `updated_at`)
- `DELETE /api/notes/{id}`
- 18 new tests in `test_notes_api.py`

Frontend:
- New `NotesPanel.tsx` replaces the placeholder on the dossier
- Inline create with type + tags + optional version target
- Filter by type + tag
- Edit-in-place
- Delete with `window.confirm` (good enough for personal-first; replace later if multi-user)
- Notes group by target on display: strategy-level / per-version / linked-to-runs/trades
- Color-coded type chips

Also: `frontend/app/journal/page.tsx` had to add `note_type: "observation"` to its create payload since the schema field is no longer optional in TS.

### `feat/experiment-ledger`

Backend:
- New `Experiment` table (created via `Base.metadata.create_all()`, no ALTER needed)
- Fields: `strategy_version_id`, `hypothesis`, `baseline_run_id`, `variant_run_id`, `change_description` (markdown), `decision`, `notes`, `created_at`, `updated_at`
- `EXPERIMENT_DECISIONS` vocabulary: `pending, promote, reject, retest, forward_test, archive`
- `GET /api/experiments/decisions`
- `POST /api/experiments` (validates version + run FKs)
- `GET /api/experiments` filters: `strategy_id` (joins through StrategyVersion), `strategy_version_id`, `decision`
- `GET /api/experiments/{id}`, `PATCH /api/experiments/{id}` (sets `updated_at`), `DELETE /api/experiments/{id}`
- 18 new tests in `test_experiments_api.py`

Frontend:
- New `ExperimentsPanel.tsx` on the dossier
- Inline create form (version, hypothesis, baseline + variant runs picked from this strategy's runs, change description, decision)
- Decision editable inline via dropdown — most common edit path
- Decision badge color-coded
- Delete with `window.confirm`
- **Intentionally minimal** — no full edit-in-place for hypothesis/change description, no metrics comparison between baseline vs variant runs. UI shape is up for review before more polish.

Doc breadcrumbs:
- `PHASE_1_SCOPE.md` and `PROJECT_CONTEXT.md` got top-of-file banners pointing at `ARCHITECTURE.md` §0 for current direction.

## Verification

All branches: `pytest backend/tests/` green at 117/117. `tsc --noEmit`, `next lint`, `next build` all green on the tip.

## What to verify on return

Before merging anything, recommend running locally:

1. `git checkout feat/experiment-ledger`
2. Backend: `python -m app.main` (or however the dev server starts)
3. Frontend: `npm --prefix frontend run dev`
4. Walk through:
   - `/strategies` — toggle board ↔ table
   - Open a strategy — see stage chip, archive button, latest metrics, **NotesPanel**, **ExperimentsPanel**
   - Create an observation note, hypothesis note. Filter by type. Edit. Delete.
   - Create an experiment. Pick baseline + variant runs. Change decision via dropdown. Delete.
   - Try to delete a strategy that has versions — should 409
   - Try to delete a version that has runs — should 409
   - Archive + unarchive a strategy and a version

## Decisions deferred for human input

These are points where I made a call but you might want to revisit:

1. **Notes UI uses `window.confirm` for delete.** Good enough for solo, ugly for product. Worth replacing with the inline-confirm pattern from `ArchiveStrategyButton` if you want consistency.
2. **ExperimentsPanel is barebones.** No baseline-vs-variant metrics comparison, no full edit (only decision is editable inline). Easy to add but I wanted you to see the shape first.
3. **`change_description` is freeform markdown.** Per the architecture doc, structured fields can replace it once real usage shows the right shape. Don't structure prematurely.
4. **No PATCH endpoint for moving a note between attachments** (e.g., reattach from strategy to version). Notes can only be created with their attachment fixed. If you want to move a note, current behavior is delete-and-recreate. If that's annoying in practice, add it.
5. **The `note_type: "ai_idea"` is intentionally absent.** Architecture doc says "add when AI generation exists." Holds.
6. **Branch naming followed the new `feat/...` pattern**, not the existing `task/...` pattern most branches use. If Husky prefers `task/...` for consistency, rename before merge.

## What was NOT built (deferred per the doc)

Per `CLAUDE.md` and `ARCHITECTURE.md` §0:

- No in-app LLM chat
- No local LLM infra
- No AI Prompt Generator yet (next after Experiment Ledger)
- No Forward/Live Drift Monitor
- No Risk Profile Manager
- No In-App Strategy Engine
- No destructive cascade deletes anywhere

## Suggested merge order

1. Merge `task/strategy-editor-pipeline` → `main` first (foundation: archive + dossier polish + vision docs)
2. Then `feat/research-workspace` → `main` (Notes)
3. Then `feat/experiment-ledger` → `main` (Experiments backend + scaffold UI)

Or, if you want to keep `feat/experiment-ledger` open for UI iteration:

1. Merge `task/strategy-editor-pipeline` → `main`
2. Merge `feat/research-workspace` → `main`
3. Keep `feat/experiment-ledger` as a working branch, polish UI, then merge

## Next phase per the architecture build order

After these merge: **AI Prompt Generator**. The endpoint should bundle strategy context + version rules + recent notes + metrics + autopsy + linked runs into a copyable prompt for Claude/GPT. No in-app chat. Mode picker: Researcher, Critic, Statistician, Risk Manager, Engineer, Live Monitor.
