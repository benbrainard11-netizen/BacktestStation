# STATUS_TAXONOMY — how we classify everything in this project

_Adopted 2026-05-17. Applied via `docs/SYSTEM_MAP.md`._

Every meaningful item in the project (file, script, doc, table, R2 prefix) should be classifiable under one of six statuses. When something can't be classified, it's `unknown` and that's a flag for cleanup.

## The 6 statuses

### `core`

**Load-bearing. Cannot be removed without breaking the system.**

Examples: `backend/app/db/models.py`, `data/meta.sqlite`, R2 `_research_inventory.json`, the v8a simulator code (when frozen).

Rules:
- Changes need extreme care. Test broadly before committing.
- Schema changes need migration handling per CLAUDE.md.
- Deletion is essentially never the right answer.

### `active`

**Currently in use. Safe to modify with normal care.**

Examples: today's audit scripts (`v18_tbbo_comparison.py`), current experiment dirs, this taxonomy doc itself.

Rules:
- Normal PR review.
- Update related docs when changing.
- Can be archived later when superseded.

### `reference`

**Historical context. Kept for understanding but not changing.**

Examples: superseded writeups (`TYPE_B_DEPLOY_CANDIDATE_2026_05_16.md` after 05_17 lands), v13-v19 audit results once locked walk-forward is done.

Rules:
- Don't modify casually. If you need to update reference material, that usually means it's actually still `active`.
- Safe to ignore in routine work.
- Don't delete; future you may need the history.

### `deprecated`

**Replaced by newer thing. Will be archived in the next sweep.**

Examples: `v14_level_reactions_audit.py` (null result, waiting on schema update from 247 before it would be useful), old prompts that have been amended.

Rules:
- Don't extend or build on top of.
- Mark with a comment pointing to the replacement when known.
- Eligible for archive at the next cleanup sprint.

### `archived`

**Moved out of active workspace (e.g., to `experiments/archive/`). Out of mind but on disk.**

Examples: experiment dirs from May 15-16 (just archived today), old GPU runs.

Rules:
- Not part of current operating system.
- Tooling should not depend on archived items existing.
- Restoration is allowed if something was archived too aggressively.

### `unknown`

**Default. Not yet classified.**

Anything not explicitly listed in `SYSTEM_MAP.md` is `unknown`. The goal is to keep this set small.

Rules:
- Treat as a tech-debt indicator.
- On encountering an unknown, classify it then update `SYSTEM_MAP.md`.

## How to apply the taxonomy

### When adding new things

Every new file, script, doc, table, or R2 prefix should be classified as `core` or `active` from creation. If you don't know which, default to `active`.

Update `docs/SYSTEM_MAP.md` in the same commit (when it's a notable item; routine code edits don't need a map update).

### Promotion / demotion

| Transition | When |
|---|---|
| active → core | Something becomes load-bearing (referenced by many things, depended on for production) |
| active → reference | Work completes, results are stable, no further changes expected |
| active → deprecated | A newer thing replaces it but we keep the old one for now |
| deprecated → archived | Next cleanup sweep moves it out of the active workspace |
| any → unknown | Discovery that we don't know what this is anymore (signals cleanup work) |

### Cleanup sprints

Periodically (~monthly), do a sweep:
1. Find all `unknown` items and classify them
2. Find all `deprecated` items and archive them
3. Find anything that drifted from `core` (no longer load-bearing) and demote to `reference`

This is how the project stays operable as it grows.

## Anti-patterns

- **"It might be useful later" hoarding.** If it's `deprecated` and no clear use case, archive it. Don't let unclassified files accumulate.
- **Marking things `core` defensively.** Only `core` for true load-bearing. Most stuff is `active` or `reference`.
- **Updating `STATUS_TAXONOMY.md` instead of `SYSTEM_MAP.md`.** This file describes the rules. The map describes the current state. Don't edit this file when reality changes; edit the map.

## Concrete rule for AI agents (Claude / 247 / 5.5 Pro)

When proposing work or recommendations:
- Identify the status of each item touched
- Don't propose modifying `core` files without escalation
- When introducing a new artifact, suggest a status for it
- Prefer extending `active` items over creating new ones

This avoids the "AI creates a new file every time" sprawl that's how this project got messy in the first place.
