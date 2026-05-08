# Research Detectors

How to add a new research-event detector to BacktestStation. Detectors
write `ResearchEvent` rows that future studies analyze.

Cross-links: [`RESEARCH_KNOWLEDGE_LAYER.md`](RESEARCH_KNOWLEDGE_LAYER.md)
(taxonomy), [`ARCHITECTURE.md`](ARCHITECTURE.md), [`ROADMAP.md`](ROADMAP.md).

## What a detector is

A detector is a stateless module that takes:
- a list of symbols
- a date range
- a `bar_reader` callable (signature mirrors `app.data.reader.read_bars`)
- an optional `mode` string (detector-defined)

…and returns a list of `ResearchEventCreate` payloads. The scan
orchestrator handles persistence (idempotent `record_event`).

Detectors do NOT:
- write to the database directly
- place trades, modify orders, or affect live behavior
- import LLM/agent libraries
- read non-market data (no journals, no notes — those belong to
  studies/decisions, not detectors)

## Architecture

```
backend/app/research/
├── sessions.py              # Globex week/day boundaries (pure)
├── reference_levels.py      # period highs/lows (pure)
├── scan.py                  # ScanResult + run_scan orchestrator
└── detectors/
    ├── __init__.py          # Detector protocol + registry
    └── <your_detector>.py   # one detector per file

backend/app/cli/scan_research_events.py     # CLI entry point
backend/app/services/research_events.py     # write-side: make_event_id, record_event
backend/app/api/research_events.py          # read-side: GET /api/research/events
```

The detector is `Detector` (Protocol) — it's structurally typed, so
any class with `feature_name`, `detector_version`, `supported_modes`,
and `scan(ctx) -> list[ResearchEventCreate]` is a valid detector.

## Adding a new detector — checklist

1. **Pick a stable name.** Snake_case slug. Examples:
   `smt_htf_reference_divergence`, `psp_formation`, `cvd_price_divergence`,
   `prior_level_sweep`, `fvg_creation`.

2. **Decide modes (if any).** Modes are detector-specific knobs that
   change reference period or tracking timeframe — e.g. SMT has
   `weekly_smt` (4H tracking) and `previous_day_smt` (1H tracking).
   If your detector has only one variant, leave `supported_modes`
   empty and ignore `ctx.mode`.

3. **Implement the class.** One file under
   `backend/app/research/detectors/`. Follow the SMT detector as a
   template:

   ```python
   class MyDetector:
       feature_name: str = "my_detector"
       detector_version: str = "v1"
       supported_modes: tuple[str, ...] = ()

       def scan(self, ctx: DetectorContext) -> list[ResearchEventCreate]:
           events = []
           for symbol in ctx.symbols:
               bars = ctx.bar_reader(
                   symbol=symbol, timeframe="1m",
                   start=..., end=...,
               )
               # detection logic
               # for each detection, append ResearchEventCreate(...)
           return events
   ```

4. **Register at module bottom:**

   ```python
   from app.research.detectors import register
   register("my_detector", MyDetector())
   ```

5. **Side-effect import** in `backend/app/research/detectors/__init__.py`:

   ```python
   from app.research.detectors import (  # noqa: E402,F401
       smt_htf_reference_divergence,
       my_detector,   # ← add this
   )
   ```

6. **Tests.** One test file per detector under `backend/tests/`. Use
   the `FakeBarReader` pattern from `tests/test_smt_htf_detector.py`:
   inject synthetic OHLC frames; assert detection rules; verify
   `event_data` shape; cover idempotence on full re-scan.

7. **Run the scan via CLI** to confirm it works on real data:

   ```powershell
   python -m app.cli.scan_research_events --list
   python -m app.cli.scan_research_events `
       --detector my_detector `
       --symbols NQ.c.0 ES.c.0 `
       --start 2026-04-01 --end 2026-05-08 `
       --dry-run
   ```

## Required fields on ResearchEventCreate

Per `app/schemas/research_events.py`:

| Field | Required? | What it is |
|---|---|---|
| `feature_name` | yes | Match your detector's `feature_name` |
| `event_type` | yes | Detector-defined sub-type (e.g. `weekly_smt`, `psp_long`) |
| `bar_end_utc` | yes | The candle that triggered the event |
| `primary_symbol` | yes | The symbol the event is "about" |
| `symbols` | yes | All symbols involved (≥1, primary included) |
| `timeframe` | yes | Tracking timeframe label (`"1m"`, `"4H"`, `"1d"`) |
| `event_data` | yes | Detector-specific dict |
| `side` | optional | `"high" \| "low" \| "bullish" \| "bearish"` etc. |
| `knowledge_card_id` | optional | FK to a `KnowledgeCard` (concept link) |
| `context` | optional | Universal context (session, day-of-week, regime) |
| `outcomes` | optional | Forward-window observations (post-event) |
| `replay_pointer` | optional | Hint for the replay UI |
| `source_run_id` | optional | If detector ran inside a backtest run |
| `detector_version` | optional | Recommended — use the same string as your class attribute |

## Idempotence

Don't worry about deduping in your detector. The orchestrator computes
`event_id = make_event_id(feature_name, primary_symbol, bar_end_utc, event_type)`
and `record_event` skips inserts when that id already exists.

This means: re-running the same scan over the same data is a no-op.
Detectors should be deterministic — same inputs → same outputs → same
event_ids → no duplicates.

## Conventions for `event_data`

Strategy-specific; you own the shape. But these conventions help:

- **Schema versioning.** Include `"schema_version": 1` (bump when you
  add/remove fields). Future readers can branch on version.
- **Detector version.** Include `"detector_version": "v1"` redundantly
  even though it's also a top-level column. Self-contained JSON
  survives column drops.
- **No raw timestamps as Python datetime.** Serialize to ISO strings
  inside `event_data` so the JSON column is portable.
- **Symbol_states pattern (from SMT).** When the event has per-symbol
  context, nest under `symbol_states: {SYMBOL: {...}}`.
- **Later-confirmation pattern (from SMT).** When relevant, add
  `later_confirmations: [{symbol, time, price}]` for symbols that
  confirmed the pattern after the primary event.

## Conventions for `outcomes`

Outcomes are forward-window observations — what happened AFTER the
event fired. Keep them sparse in v1 of any detector; add only after
detection is stable. Pattern:

```python
outcomes = {
    "schema_version": 1,
    "horizon_4h": {
        "n_candles": 1,
        "mfe_pts": 25.0,
        "mae_pts": -8.0,
        "close_return_pct": 0.4,
    },
    "horizon_1d": {...},
}
```

Forward-window computation can live in a sibling
`outcomes/<detector>.py` that runs as a post-processor, leaving the
detector itself focused on detection.

## Don'ts

- **Don't** write events directly to the DB — return them from
  `scan()` and let the orchestrator handle it.
- **Don't** silently swallow errors during detection; let them bubble
  to the orchestrator which records them as `n_errors`.
- **Don't** depend on global state — everything comes through
  `DetectorContext`.
- **Don't** modify symbols/dates inside the detector — they're inputs.
- **Don't** add detectors that produce >1000 events per period without
  explicit pagination strategy. The DB grows fast.

## Currently registered detectors

Run `python -m app.cli.scan_research_events --list` to see live state.
At time of writing:

- `smt_htf_reference_divergence` v1 — modes: `weekly_smt`,
  `previous_day_smt`.

## Where new detectors go (priority order)

Per `RESEARCH_KNOWLEDGE_LAYER.md`'s SMT walkthrough, future detectors
likely include:

1. PSP formation (continuation/reversal candle pattern)
2. CVD/price divergence
3. Liquidity sweep (PDH/PDL/PWH/PWL takes)
4. FVG creation + mitigation
5. Displacement candle

Each gets its own file. Each registers under a stable name. Each has
its own test file.
