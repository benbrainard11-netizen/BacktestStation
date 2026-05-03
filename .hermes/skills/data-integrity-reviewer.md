# Skill: data-integrity-reviewer

Decide whether BacktestStation's data is currently trustworthy enough to act
on. Read the snapshot script output, recent logs, and (if available) test
output, then return a clear verdict with a fix-priority list.

## When to use this skill

- Before running a backtest Ben intends to act on.
- After a data pull, ingester restart, or scheduled-task change.
- After any error or warning in the live pipeline.
- During the morning status review.

## What this skill must NOT do

- Do not pull paid Databento data to "investigate." Read what already
  exists; if more data is needed, recommend a paid pull and wait for Ben's
  approval.
- Do not modify SQLite, parquet, raw DBN, or scheduled tasks.
- Do not declare data trustworthy without checking all five inputs below
  (or noting which ones were unavailable).
- Do not give a soft verdict. Pick trustworthy, suspicious, or broken — not
  "looks mostly fine."

## Inputs to read

For each input, note whether it was available, missing, or errored. Flag
missing inputs in the output.

1. **Data health** — output of `GET /api/data-health` (warehouse contents,
   scheduled-task health, disk space).
2. **Monitor status** — output of `GET /api/monitor/live` and
   `/api/monitor/ingester` (live ingester heartbeat, last tick).
3. **Knowledge health** — output of `GET /api/knowledge/health` (stale
   cards, broken references).
4. **Dataset coverage / readiness** — output of `GET /api/datasets/coverage`
   and `/api/datasets/readiness` (per-symbol, per-day coverage; gaps).
5. **Recent logs** — tail of `data/live_inbox/import.log` and any other
   log surfaced by the snapshot script.
6. **Test output** — if `pytest -q` was run recently, include pass/fail
   summary. If not run, say so; do not run paid-data tests.

The simplest way to gather these in one shot is to run
`scripts/hermes_status_snapshot.ps1` first.

## Output format

Every data-integrity-reviewer output must use exactly these sections, in
this order:

### Trustworthy
Bulleted list of signals that look good. Each bullet names the source
(e.g. "data-health: scheduled task `bs-scan-datasets` ran 14m ago, 0
errors").

### Suspicious
Bulleted list of signals that are off but not yet broken. Examples:
- a coverage gap on a single day for a single symbol
- a stale knowledge card
- an ingester heartbeat older than expected but younger than the alert
  threshold
- a warning in `import.log` that has not yet recurred

For each item, name the source, the symptom, and what would escalate it to
broken.

### Broken
Bulleted list of signals that fail outright. Examples:
- live ingester heartbeat older than 5 minutes during market hours
- scheduled task last-run failed
- coverage gap that spans multiple days or all symbols
- repeated errors in `import.log`
- pytest failures

For each item, name the source and the symptom in one sentence.

### Backtest risk
One short paragraph. Translate the signals above into a risk level for an
imminent backtest, in plain English. Use one of:
- **Low risk** — backtest results can be trusted as-is.
- **Medium risk** — backtest will run but specific windows or symbols
  should be excluded; name them.
- **High risk** — do not act on backtest results until the listed broken
  items are fixed.

### Fix priority
Numbered list of fixes, ordered by urgency. Each item:
- the symptom
- the smallest action that resolves it
- whether it requires Ben's approval (paid pull, schema change, etc.)

If a fix would require a paid Databento pull, mark it with **(paid —
needs Ben approval)** and include a rough cost estimate if possible.

## Quality checks before returning the review

1. Did you actually look at all five input categories? Missing inputs must
   be called out, not silently skipped.
2. Did the verdict in "Backtest risk" match the bullets above it? A "low
   risk" verdict with three items in "broken" is a contradiction.
3. Is the fix-priority list ordered by impact, not by ease?
4. Did anything paid get flagged with **(paid — needs Ben approval)**?

If any check fails, redo the review.
