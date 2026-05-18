# CLI Design — `bs` command surface

_Spec for `backend/scripts/cli/`. Implementation owner: 247. Spec owner: benpc._

## Goal

One canonical command-line tool the operator runs. Replaces "remember which Python script to invoke." Every subcommand wraps existing functionality (don't reinvent).

## Invocation

```
bs <verb> <object> [options...]
```

Installed via `pyproject.toml` console_scripts entry. The `bs` binary lives in the project venv.

## Output conventions

- Text output by default (human-readable, multi-line, ASCII tables OK)
- `--json` flag everywhere for machine output
- Errors to stderr; exit 1 on failure, 2 on usage error
- All commands accept `--help`

## v1 surface (the 8 commands that ship in week 1)

### `bs doctor`

Health check across the whole project.

```
bs doctor
bs doctor --json
```

Checks:
- `data/meta.sqlite` opens, expected tables present
- R2 reachable + credentials valid (head_object on `_research_inventory.json`)
- Local data dirs exist (`data/research_events`, `data/ml/levels`, etc.)
- Python venv has required deps (boto3, pandas, sqlalchemy)
- `D:/data/` mounted and readable
- Git working tree clean status reported (not failure on dirty)
- Recent test suite pass status (if `pytest --collect-only` returns errors, flag)

Exit codes: 0 = all green, 1 = at least one check failed.

### `bs status`

Overall project snapshot.

```
bs status
bs status --json
```

Shows:
- Current branch + commits ahead/behind origin
- Active candidates by lifecycle status (from `strategy_versions.status`)
- Last 5 trial groups
- Last 5 dataset snapshots
- Recent backtest runs

### `bs data validate <snapshot_id>`

Run validation gates against a snapshot's partitions.

```
bs data validate <snapshot_id> [--schemas ohlcv-1m,tbbo] [--quick]
```

Wraps the validation runner (Phase 2 deliverable). Writes a `partition_validation_reports` row + findings. Prints summary.

`--quick`: skip slow gates (full file hash, deep parquet inspection).

### `bs data inventory`

Wraps `scripts/data_inventory_report.py`. Generates a fresh inventory report.

```
bs data inventory [--quick]
```

### `bs snapshot create`

Wraps `backend/scripts/data/create_snapshot.py`.

```
bs snapshot create --symbols NQ.c.0,ES.c.0 \
                   --schemas ohlcv-1m \
                   --date-start 2018-01-01 \
                   --date-end 2026-05-15 \
                   [--name "v21_holdout"] \
                   [--with-hash] \
                   [--dry-run]
```

Returns the new `snapshot_id`. With `--dry-run`, walks data but skips DB write.

### `bs snapshot list`

```
bs snapshot list [--status active|archived|all] [--limit 20]
```

### `bs snapshot show <snapshot_id>`

```
bs snapshot show <snapshot_id>
```

Shows metadata + partition count + validation status.

### `bs trial list`

```
bs trial list [--hypothesis-id N] [--status running|completed|...]
```

## v2 surface (next batch, week 2)

These ship after v1 lands cleanly. Document the surface now so v1 doesn't need refactoring.

| Command | Purpose |
|---|---|
| `bs trial create` | Create a hypothesis + trial group + initial trials |
| `bs trial lock` | Create a `trial_lock_records` row (pre_validation / pre_test / final) |
| `bs trial run <trial_id>` | Execute a trial via existing simulator code |
| `bs candidate list` | List `strategy_versions` filtered by status |
| `bs candidate show <id>` | Full candidate detail with linked trials |
| `bs candidate promote <id> --to <status>` | State transition with required-gate validation |
| `bs candidate kill <id> --reason ...` | Explicit kill (per CANDIDATE_LIFECYCLE) |
| `bs paper start <candidate_id>` | Begin paper-trade tracking |
| `bs paper report` | Drift report (paper vs backtest) |

## v3 surface (later)

| Command | Purpose |
|---|---|
| `bs r2 status` | R2 inventory health |
| `bs r2 sync` | Trigger publish |
| `bs r2 download <pattern>` | Pull from R2 |
| `bs db migrate` | Run pending migrations explicitly (currently auto) |
| `bs db backup` | Snapshot the meta.sqlite |

## File structure

```
backend/scripts/cli/
    __init__.py
    main.py             # Typer app, dispatches to subcommands
    cmd_doctor.py
    cmd_status.py
    cmd_data.py         # validate, inventory
    cmd_snapshot.py     # create, list, show
    cmd_trial.py        # list initially
    cmd_candidate.py    # placeholder for v2
    cmd_paper.py        # placeholder for v2
    output_format.py    # shared text/json formatters
```

Each `cmd_*.py` registers its subcommands with the main Typer app.

## Implementation order

1. **`main.py` skeleton + `cmd_doctor.py`** — proves the framework. Doctor wraps existing checks.
2. **`cmd_status.py`** — read-only, easiest wins.
3. **`cmd_data.py`** — wraps `data_inventory_report.py` + validation.
4. **`cmd_snapshot.py`** — wraps `create_snapshot.py` + list/show queries.
5. **`cmd_trial.py list`** — simple SELECT against trial registry.

Total: ~1 day if 247 stays focused. Tests inline as each command lands.

## Testing

Each subcommand gets at least:
- `--help` doesn't crash
- One happy-path test with mock data
- One failure-path test (missing arg, invalid input)

Test file: `backend/tests/test_cli.py`. Use Typer's `CliRunner`.

## Anti-patterns to avoid

- **Don't reinvent existing functions.** If `scripts/data_inventory_report.py` works, wrap it; don't rewrite the logic in `cmd_data.py`.
- **Don't add interactive prompts in v1.** All commands run unattended; flags only.
- **Don't add color/spinners.** Plain text. Color/UX polish is v3 or later.
- **Don't try to ship all 20+ commands at once.** v1 ships 8. v2 adds 9. v3 is later.

## Dependencies

- `typer` (for Click-style command parsing with type hints) — add to `pyproject.toml`
- Existing project deps (sqlalchemy, boto3, pandas)
- No new external services

## Out of scope

- Web UI for the CLI commands (that's the Dashboard project)
- Cross-platform packaging (Linux/Mac) — Windows-first for now
- Shell completion — nice-to-have, v3+
- Plugin/extension system — overkill for solo lab
