# Session notes — 2026-04-24

> Temporary doc. Delete once Ben + Husky review and decide what to merge.

This session ran in two phases. Ben left for the gym partway through, came back, then handed me a real autonomous run (plan-mode-approved). Four branches stacked, nothing pushed, nothing merged, no PRs opened.

## Branch chain

```
main
└─ task/strategy-editor-pipeline   (+4)  archive lifecycle + dossier polish + docs alignment
   └─ feat/research-workspace      (+3)  Notes Workspace
      └─ feat/experiment-ledger    (+4)  Experiments backend + scaffold UI + doc breadcrumbs
         └─ feat/prompt-generator  (+5)  AI Prompt Generator + UX polish + run-detail notes + branch audit
```

Tip is `feat/prompt-generator`. To inspect each layer:

```bash
git checkout task/strategy-editor-pipeline   # archive lifecycle + dossier polish + docs
git checkout feat/research-workspace          # adds: Notes panel
git checkout feat/experiment-ledger           # adds: Experiment ledger backend + scaffold UI
git checkout feat/prompt-generator            # adds: AI Prompt Generator + polish + run-detail notes
```

## What's on each branch

### `task/strategy-editor-pipeline`

Backend:
- `archived_at` column on `StrategyVersion` (idempotent ALTER)
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
- `CLAUDE.md` extended "What not to build yet" + Schema migration discipline section

### `feat/research-workspace`

Backend:
- `Note` extended: `strategy_id`, `strategy_version_id`, `note_type`, `tags`, `updated_at` (idempotent ALTERs)
- `NOTE_TYPES` vocabulary: `observation, hypothesis, question, decision, bug, risk_note`
- `GET /api/notes/types`
- `POST /api/notes` accepts new fields + validates + normalizes tags
- `GET /api/notes` accepts `strategy_id`, `strategy_version_id`, `note_type`, `tag` filters
- `PATCH /api/notes/{id}` (sets `updated_at`)
- `DELETE /api/notes/{id}`
- 18 new tests in `test_notes_api.py`

Frontend:
- New `NotesPanel.tsx` replaces the placeholder on the dossier
- Inline create with type + tags + optional version target
- Filter by type + tag
- Edit-in-place
- Notes group by target on display: strategy-level / per-version / linked-to-runs/trades
- Color-coded type chips

Also: `frontend/app/journal/page.tsx` had to add `note_type: "observation"` to its create payload since the schema field is no longer optional in TS.

### `feat/experiment-ledger`

Backend:
- New `Experiment` table (created via `Base.metadata.create_all()`, no ALTER needed)
- Fields: `strategy_version_id`, `hypothesis`, `baseline_run_id`, `variant_run_id`, `change_description`, `decision`, `notes`, timestamps
- `EXPERIMENT_DECISIONS` vocabulary: `pending, promote, reject, retest, forward_test, archive`
- `GET /api/experiments/decisions`
- `POST /api/experiments` (validates version + run FKs)
- `GET /api/experiments` filters: `strategy_id` (joins through StrategyVersion), `strategy_version_id`, `decision`
- `GET /api/experiments/{id}`, `PATCH /api/experiments/{id}` (sets `updated_at`), `DELETE /api/experiments/{id}`
- 18 new tests in `test_experiments_api.py`

Frontend:
- New `ExperimentsPanel.tsx` on the dossier
- Inline create form (version, hypothesis, baseline + variant runs, change description, decision)
- Decision editable inline via dropdown
- Decision badge color-coded
- (Polish landed in the next branch)

Doc breadcrumbs:
- `PHASE_1_SCOPE.md` and `PROJECT_CONTEXT.md` got top-of-file banners pointing at `ARCHITECTURE.md` §0.

### `feat/prompt-generator` (NEW — autonomous run)

Backend:
- New `Experiment`-style table is NOT required — this is purely a service that bundles existing data
- `app/services/prompt_generator.py` — pure DB read + string assembly
  - Bundles: strategy meta, active versions, last 20 notes (scoped to strategy + its versions), last 10 experiments, latest backtest run + RunMetrics, autopsy when ≥5 trades
  - Skips archived versions
  - Mode preamble vocabulary: `researcher, critic, statistician, risk_manager, engineer, live_monitor`
- `app/schemas/prompts.py` with `PROMPT_MODES`, `PromptModesRead`, `PromptGenerateRequest` (strategy_id + mode + optional focus_question), `PromptGenerateResponse` (prompt_text + mode + bundled_context_summary + char_count)
- `GET /api/prompts/modes` vocabulary endpoint
- `POST /api/prompts/generate` returns markdown blob + summary
- 13 new tests in `test_prompts_api.py` covering mode validation, focus question, mode preamble switching, every section's inclusion, autopsy threshold (≥5 trades), no-versions case, archived-version skipping, 404, 422

Frontend:
- New `PromptGeneratorPanel.tsx` on the dossier (below ExperimentsPanel)
  - Mode dropdown with description hints
  - Optional focus question input
  - Generate → result in read-only textarea + Copy button (flashes "copied ✓" for 2s)
  - Char count + bundled-context summary visible
- Pure copy-out workflow — the app makes NO LLM calls

UX polish:
- Replaced `window.confirm` delete in NotesPanel + ExperimentsPanel with inline confirm matching `ArchiveStrategyButton`. No more OS dialogs.
- ExperimentsPanel now supports full edit-in-place (hypothesis / change_description / notes were view-only before; only decision was editable).
- ExperimentsPanel renders a baseline-vs-variant metrics comparison table (Net R, Win rate, Profit factor, Max DD, Trades + signed delta column) when both runs are linked. Lazy-fetches metrics on item mount. Delta column color-codes positive/negative.

Run detail page:
- New `RunNotesSection.tsx` mounted on `/backtests/[id]` below the Trades table. Filters notes by `backtest_run_id`. Same type chips + edit/delete + inline confirm as the dossier panel, but flat (no version dropdown, no grouping). Kept as a separate component rather than over-generalizing NotesPanel.

Docs:
- New `BRANCH_AUDIT.md` at repo root. 30 of 35 non-main branches are merged and safe to delete; 4 are this session's stack; 1 (`review/frontend-monitor`) is stale and divergent. Includes the suggested `git branch -d` command. I did NOT delete any branches.

## Verification (final state)

- `pytest backend/tests/ -q` → **130 passed** (+13 new prompt tests on top of the 117 from earlier)
- `tsc --noEmit` clean
- `next lint` clean (0 warnings)
- `next build` clean (8 routes generate)
- Working tree clean on `feat/prompt-generator`

## What to verify on return

```bash
# 1. Walk the new tip
git checkout feat/prompt-generator

# 2. Backend + frontend dev servers
# (run them however you usually do — separate terminals)

# 3. Click through:
```

- `/strategies` — toggle board ↔ table
- Open a strategy:
  - **Stage chip** with colored dot near header
  - **Archive button** with inline confirm
  - **Latest run metrics** panel
  - **NotesPanel** — create observation + hypothesis + risk_note. Filter by type + tag. Edit. Delete (inline confirm now, not OS dialog).
  - **ExperimentsPanel** — create with baseline + variant runs. Edit hypothesis + change in place. Change decision via dropdown. If both runs have metrics, see the side-by-side compare table. Delete with inline confirm.
  - **PromptGeneratorPanel** — pick a mode (try `critic` and `statistician` for variety), add a focus question if you have one, Generate, Copy, paste into a fresh Claude or GPT chat, confirm the prompt reads coherently and includes the right context
- Open a run detail page:
  - Scroll to the new **Notes** panel below Trades. Create a note. Edit. Delete.
- Try `/api/strategies/{id}` DELETE on a strategy with versions → 409
- Try `/api/strategy-versions/{id}` DELETE on a version with runs → 409
- Read `BRANCH_AUDIT.md`, run the suggested cleanup if you agree

## Decisions deferred for human input

These are points where I made a call but you might want to revisit:

1. **Prompt format defaults to markdown with `##` sections.** Reasonable default, but if you want XML tags / YAML / terser format, it's a small edit in `prompt_generator.py`. The `MODE_PREAMBLES` dict is also where you'd tune the persona text.
2. **Autopsy is included only when ≥5 trades exist.** Threshold is in `prompt_generator.py:_autopsy_section`. Tune if it's too high/low for your typical strategies.
3. **Notes/Experiments cap.** Last 20 notes, last 10 experiments. `NOTE_LIMIT` and `EXPERIMENT_LIMIT` constants at the top of the service.
4. **`ai_idea` note type still absent.** Per architecture doc, add when AI generation actually exists. You could argue PromptGenerator counts now — but its output goes back as a regular note manually, not through a special channel.
5. **RunNotesSection is its own component, not a generalized NotesPanel.** I judged the prop divergence (no version dropdown, no grouping) made sharing more complex than helpful. Reasonable people could go the other way.
6. **Branch naming followed `feat/...` pattern.** Existing branches use `task/...`. If Husky prefers consistency, rename before merge: `git branch -m feat/prompt-generator task/prompt-generator`.

## What was NOT built (deferred per the doc)

Per `CLAUDE.md` and `docs/ARCHITECTURE.md` §0:

- No in-app LLM chat
- No local LLM infra
- No engine work (`backend/app/engine/` untouched)
- No Forward/Live Drift Monitor (touches the live system, real product calls needed)
- No Risk Profile Manager (real-money adjacent, defer)
- No In-App Strategy Engine
- No destructive cascade deletes anywhere
- No remote pushes, merges, or PRs

## Suggested merge order

1. `task/strategy-editor-pipeline` → `main` (foundation: archive + dossier polish + vision docs)
2. `feat/research-workspace` → `main` (Notes)
3. `feat/experiment-ledger` → `main` (Experiments)
4. `feat/prompt-generator` → `main` (AI Prompt Generator + polish + run notes + audit)

If you want to keep #4 open for product iteration on prompt format / mode preambles, that's fine — the work below it stands on its own.

## Next phase per architecture build order

After these merge: **Forward/Live Drift Monitor** (#7 in build order). I deferred it autonomously because it touches the live signal flow and requires product calls about what "drift" means concretely. Worth a planning discussion with Husky before code starts.
