# NQ OR-High Middle-Third Paper Monitor

## Purpose

This is the first live-paper layer for the frozen OR-high middle-third prototype.

It is a shadow paper monitor. It does not send broker orders and it does not trade real money.

The goal is to watch the live market, apply the exact frozen research rules, simulate paper entries/stops/targets, and write logs that can be reviewed after the session.

## Frozen Rules

- Symbol: `NQ.c.0`
- Opening range: 09:30-10:00 ET
- Required context: opening-range close in the middle third
- Trade direction: OR-high first break only
- Stop: OR low
- Target: OR high plus one opening-range width
- Slippage: 1 tick
- Commission: $2.00 per side
- Quantity: 1 NQ contract
- Forced flat: 16:00 ET
- Frozen research commit: `d28781e`

The monitor tracks all three frozen entry styles for comparison:

- `immediate_break`
- `first_retest`
- `confirmation_30s`

The default paper-account style is `immediate_break`. That keeps the account-style P&L to one paper trade path instead of mixing three variants together.

## How To Run Once

```powershell
cd backend
.\.venv\Scripts\python.exe -m app.cli.nq_or_high_middle_third_paper_monitor
```

## How To Run Continuously

```powershell
cd backend
.\.venv\Scripts\python.exe -m app.cli.nq_or_high_middle_third_paper_monitor --loop --poll-seconds 30
```

Leave that terminal open during the session. Stop it with `Ctrl+C`.

## Auto Session Mode

For the normal paper-trading day, use:

```powershell
cd backend
.\.venv\Scripts\python.exe -m app.cli.nq_or_high_middle_third_paper_monitor --auto-session --poll-seconds 30 --stop-after-report
```

This mode:

- polls throughout the session
- detects when new 1m bars or event data arrive
- runs the existing DBN-to-parquet mirror automatically on local warehouse machines
- skips the mirror automatically when `BS_DATA_BACKEND=r2`
- writes a daily report after the 16:00 ET close

If the live Databento DBN ingester is already running on the same machine, the auto mirror step can convert mature DBN chunks into read-side parquet. If this machine is only reading R2, the monitor cannot create new Databento data itself; it waits for R2 to receive updated partitions and reports missing data honestly.

To disable the mirror even in auto-session mode:

```powershell
.\.venv\Scripts\python.exe -m app.cli.nq_or_high_middle_third_paper_monitor --auto-session --no-auto-mirror
```

## Output Files

Default folder:

`data/live_paper/nq_or_high_middle_third`

Files:

- `paper_snapshot.json` - latest monitor state
- `paper_positions.csv` - current paper state for each frozen entry style
- `paper_snapshots.jsonl` - append-only run snapshots
- `paper_signals.jsonl` - append-only signal log
- `paper_closed_trades.jsonl` - append-only closed paper trades
- `reports/paper_daily_YYYY-MM-DD.md` - end-of-day beginner report
- `reports/paper_daily_YYYY-MM-DD.json` - machine-readable daily report

The monitor also writes:

`data/live_status.json`

That is the existing BacktestStation monitor heartbeat. The `/monitor` page already polls it.

## Beginner Read

This is the right next step before broker paper trading.

It answers:

- Did the setup appear live?
- Did the monitor detect it at the correct time?
- Which frozen entry style would have entered?
- Was the trade open, stopped, targeted, or forced flat?
- Did the live behavior match the historical research assumptions?
- Was data missing or delayed?
- Was the live monitor using MBP-1 or TBBO fallback data?

It does not answer:

- Whether a broker API can place orders correctly
- Whether broker fills match our simulated fills
- Whether we should change the strategy rules

Those come later, after this shadow paper monitor behaves cleanly.

## Live Data Truth

The historical research was MBP-1 based. The repo's live Databento ingester is TBBO based. The paper monitor therefore prefers MBP-1 if today's partition exists and falls back to TBBO when that is the live data available.

Every heartbeat and daily report records `event_schema_used`, so the result is not mislabeled.

## Data Requirement

The monitor needs current 1-minute bars plus event data available through the existing BacktestStation data reader.

Preferred event data:

- MBP-1, if today's partition exists
- TBBO fallback, if live TBBO is the available real-time feed

If the data pipeline is delayed, the monitor will stay in a waiting state such as:

- `waiting_for_opening_range`
- `waiting_for_opening_range_data`
- `waiting_for_mbp_data`
- `waiting_for_or_high_break`

That is safer than pretending a trade happened.
