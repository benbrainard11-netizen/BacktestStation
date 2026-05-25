# Documentation Index

Status date: 2026-05-25

This index separates current operating docs from historical notes.

## Current Operating Docs

| Doc | Use |
|---|---|
| `README.md` | Short repo entrypoint |
| `docs/PROJECT_MAP.md` | Current project roles and truth layer |
| `docs/R2_WAREHOUSE_MAP.md` | Cloud warehouse layout and sync rules |
| `docs/SYSTEM_MAP.md` | Detailed component inventory |
| `docs/SCHEMA_SPEC.md` | Load-bearing schema contracts |
| `docs/DATA_FORMAT.md` | File layout and parquet metadata |
| `docs/AI_HANDOFF.md` | How an AI/human should resume safely |
| `docs/OPERATING_RULES.md` | Non-negotiable engineering rules |
| `docs/TABLE_REGISTRY.md` | DB table classification |
| `docs/TRIAL_REGISTRY_USAGE.md` | Trial registry examples |
| `docs/DATASET_SNAPSHOT_USAGE.md` | Dataset snapshot examples |

## Operator Scripts

| Script | Use |
|---|---|
| `scripts/workspace_health.ps1` | Read-only workspace status scan |
| `scripts/install_mbo_r2_mirror_task.ps1` | Install daily local-MBO-to-R2 mirror task |

## Active Research/Validation Docs

| Doc | Use |
|---|---|
| `docs/ML_FULL_SCOREBOARD_2026_05_15.md` | Strict-label scoreboard snapshot |
| `docs/ML_STRICT_SWEEP_RESULT.md` | Sweep strict-label result |
| `docs/ML_OB_STRICT_WALKFORWARD_2026_05_16.md` | Order-block strict walk-forward |
| `docs/RESEARCH_VALIDATION_PACKET_2026_05_17.md` | External-review packet |
| `docs/VALIDATION_DESIGN.md` | Dataset validation design |
| `docs/TBBO_RESOLVER_DESIGN_2026_05_17.md` | Honest-fill resolver design |

## Generated/Regenerated Docs

These can be refreshed by scripts and may drift between runs:

- `backend/app/research/features/*/stats.md`
- `docs/ML_SNAPSHOT_AUDIT*.md`
- `docs/ML_SNAPSHOT_LEADERBOARD*.md`
- `docs/ML_SNAPSHOT_WALK_FORWARD*.md`
- `docs/ML_DATASET_CATALOG.md`
- `docs/ASSET_UNIVERSE_MANIFEST.md`
- `docs/WAREHOUSE_ASSET_INVENTORY.md`

## Historical Docs

These are useful context but are not current operating truth by default:

- `docs/BEN_247_PROMPT_*.md`
- `docs/OVERNIGHT_*.md`
- `docs/MORNING_REPORT_*.md`
- `docs/SESSION_SUMMARY_*.md`
- `docs/archive/*.md`
- `experiments/**/SUMMARY.md`
- `experiments/**/RESULT.md`

If a historical doc contains instructions that conflict with a current map,
follow the current map unless Ben explicitly says otherwise.
