# Data ingestion

Long-running daemons that write to the BacktestStation data warehouse. These are SEPARATE PROCESSES from the FastAPI app — they don't share request handling. They read from market data sources and write to disk.

## Components

| File | Purpose | Status |
|---|---|---|
| `live.py` | Databento Live TBBO streamer | ✓ first draft |
| `historical.py` | Monthly MBP-1 batch puller | TODO |
| `parquet_mirror.py` | Periodic DBN → parquet conversion | TODO |

## Where this runs

`live.py` is meant to run **on the 24/7 collection node** (currently `insyncserver` / ben-247 on Tailscale). Not on Ben's main PC. Not on Husky's PC. The 24/7 node is the only one that can guarantee continuous market-hour coverage.

## Setup on the collection node

One-time:

```powershell
# Set the API key as a user environment variable so it persists across reboots.
[Environment]::SetEnvironmentVariable("DATABENTO_API_KEY", "db-YOUR-KEY-HERE", "User")

# Pick where data lives. Default is C:\data on Windows. Make sure the drive has
# room (TBBO on 4 symbols ≈ 100-300 MB/day → 25-75 GB/year).
[Environment]::SetEnvironmentVariable("BS_DATA_ROOT", "C:\data", "User")

# Confirm the package is installed (audit script said yes already).
pip show databento
```

## Run it interactively first (verify it works)

```powershell
cd C:\Users\benbr\BacktestStation\backend
python -m app.ingest.live
```

Watch stderr for `session started`. After ~30 seconds, look at:

```powershell
Get-Content C:\data\heartbeat\live_ingester.json
```

You should see `ticks_received` climbing and `ticks_last_60s` showing recent activity (during market hours; off-hours TBBO traffic is sparse).

Stop with **Ctrl+C**. The script handles SIGINT cleanly — closes the DBN file, flushes the heartbeat, exits.

## Run it as a service (later)

When you're confident it works, install it as a Windows service so it survives reboots. Two clean options:

### Option A: NSSM (recommended, simple)

```powershell
# Install NSSM once (https://nssm.cc/download)
nssm install BacktestStationIngester ^
  "C:\Users\benbr\AppData\Local\Programs\Python\Python312\python.exe" ^
  "-m app.ingest.live"
nssm set BacktestStationIngester AppDirectory "C:\Users\benbr\BacktestStation\backend"
nssm set BacktestStationIngester AppEnvironmentExtra DATABENTO_API_KEY=db-...
nssm start BacktestStationIngester
```

### Option B: Task Scheduler (built-in, no extra install)

Create a task that runs at startup, restarts on failure, runs whether user is logged in or not. Slightly fiddlier than NSSM but no install.

## Output layout

```
C:\data\
├── raw\
│   └── live\
│       └── GLBX.MDP3-tbbo-2026-04-25.dbn
├── heartbeat\
│   └── live_ingester.json
└── logs\
    └── live_ingester.log
```

One DBN file per UTC date. Contains all 4 symbols' TBBO records mixed (sorted by timestamp). The downstream `parquet_mirror.py` (TODO) will split into per-symbol parquet for easy query.

## Heartbeat schema

```json
{
  "status": "running",
  "started_at": "2026-04-25T13:30:00+00:00",
  "uptime_seconds": 1234,
  "last_tick_ts": "2026-04-25T13:50:33+00:00",
  "ticks_received": 47832,
  "ticks_last_60s": 145,
  "current_file": "C:\\data\\raw\\live\\GLBX.MDP3-tbbo-2026-04-25.dbn",
  "current_date": "2026-04-25",
  "symbols": ["NQ.c.0", "ES.c.0", "YM.c.0", "RTY.c.0"],
  "dataset": "GLBX.MDP3",
  "schema": "tbbo",
  "stype_in": "continuous",
  "reconnect_count": 0,
  "last_error": null
}
```

BacktestStation's `/monitor` page will eventually read this — separate work item.

## Things to know

- **TBBO not MBP-1 for live.** Databento's $180/mo CME plan only allows TBBO on the live feed; MBP-1 is historical-only.
- **Continuous symbology.** `NQ.c.0` etc. — Databento auto-resolves to current front-month, no rollover code needed here.
- **UTC date for file rotation.** Cleaner than session-close logic. CME futures have a daily settlement around 5pm ET but TBBO records flow nearly 24h.
- **Restart safety.** Append mode means a crash + restart resumes the same day's file. Some duplication possible across restart boundaries; downstream parquet conversion can dedup on `(timestamp, instrument_id, side)`.
- **No cross-talk with the live trading bot.** This script only reads market data; it does not place orders, read Rithmic, or touch the bot's state.
