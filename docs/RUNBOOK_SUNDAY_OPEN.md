# Sunday-open runbook

Pre-flight for the futures session that opens Sunday ~6pm ET (22:00 UTC). Goal: walk through this once Sunday afternoon on ben-247 (the 24/7 collection node) so the ingester collects the open without anyone watching.

## 1. Pre-open verification (run on ben-247)

Run these in order. Anything that fails → see §3.

### Ingester service

```powershell
Get-Service BacktestStationIngester
```

`Status` must be `Running`. If `Stopped`, `Start-Service BacktestStationIngester`. If the service doesn't exist, install it: `powershell -ExecutionPolicy Bypass -File scripts\install_ingester_service.ps1`.

### Scheduled tasks

```powershell
Get-ScheduledTask -TaskName BacktestStation*
```

Both tasks must be present:

- `BacktestStationParquetMirror` — hourly DBN → parquet conversion
- `BacktestStationHistorical` — monthly MBP-1 backfill (next fires May 1, 02:00 local)

If either is missing: `powershell -ExecutionPolicy Bypass -File scripts\install_scheduled_tasks.ps1`.

### Heartbeat file is fresh

```powershell
cat $env:BS_DATA_ROOT\heartbeat\live_ingester.json
```

Check:
- `status` is `"running"` (not `"stopped"` or `"error"`)
- `last_tick_ts` was within the last few minutes IF markets are open; pre-open it'll be older — that's fine, just confirm the field exists and the file isn't ancient

### Disk space

```powershell
Get-PSDrive D, F | Select-Object Name, @{N='FreeGB';E={[math]::Round($_.Free/1GB,1)}}
```

At least 10 GB free on the data drive. A weekend of TBBO is roughly 2-4 GB depending on activity.

### Manually trigger the parquet mirror once

This confirms the mixed-schema fix (commit `aa7cc82`) works on real data:

```powershell
cd C:\Users\benbr\BacktestStation\backend
.venv\Scripts\python.exe -m app.ingest.parquet_mirror --rebuild
```

Should report `errors=0`. If it reports `errors=N`, check `$env:BS_DATA_ROOT\logs\parquet_mirror.log` and stop — do not let the open run with a broken mirror, you won't have queryable data.

### Monitor page (run from main PC)

Open `http://<ben-247-tailscale-name>:8000/monitor`. The Live Ingester panel should show the heartbeat. After open, `ticks_last_60s` should climb above zero within ~30 seconds.

## 2. What "Sunday open" looks like on the wire

- **Open time:** Sunday 6:00pm ET (22:00 UTC). Globex futures (NQ, ES, YM, RTY, etc.).
- **First ticks:** within ~30 seconds of open. Usually a burst on the first minute, then steady.
- **Tick rate:** ramps over the first hour as Asian/London desks come online. Expect quiet between 7-8pm ET, busier after London opens (3am ET).
- **What success looks like by Monday morning:** `cat $env:BS_DATA_ROOT\heartbeat\live_ingester.json` shows `ticks_received` in the millions, `reconnect_count` low (single digits), `last_error` empty or stale.

## 3. If something is broken

### Heartbeat shows `last_tick_ts` > 5 minutes old during market hours

1. Check Databento status: https://status.databento.com
2. Tail the ingester log: `Get-Content $env:BS_DATA_ROOT\logs\live_ingester.log -Tail 50`
3. If the log shows reconnect attempts spinning, restart the service: `Restart-Service BacktestStationIngester`

### Service is stopped

```powershell
Start-Service BacktestStationIngester
```

If it won't start (returns immediately to `Stopped`), look at `$env:BS_DATA_ROOT\logs\live_ingester.log` for the crash. Most common cause: `DATABENTO_API_KEY` env var missing at machine scope. Fix with `setup_ingester.ps1`.

### Scheduled task didn't fire

Force a run:

```powershell
Start-ScheduledTask -TaskName BacktestStationParquetMirror
```

Check result:

```powershell
Get-ScheduledTaskInfo -TaskName BacktestStationParquetMirror | Select LastRunTime, LastTaskResult
```

`LastTaskResult` of `0` is success; anything else means the task ran but the script exited non-zero. Check `$env:BS_DATA_ROOT\logs\parquet_mirror.log`.

### Parquet mirror erroring on every file

Likely a new schema appearing in the DBN stream that `to_df()` doesn't know how to flatten. The fix from `aa7cc82` passes the schema name from the filename — if a file is named with an unknown schema, that's the bug. Check `$env:BS_DATA_ROOT\logs\parquet_mirror.log` for the offending file.

### Disk filling up faster than expected

A high-volume open (FOMC week, etc.) can write 5+ GB of TBBO over the weekend. If headed for full:
- The DBN files are immutable source-of-truth — don't delete the current day's
- Old daily DBN files in `$env:BS_DATA_ROOT\raw\live\` from prior weeks can be moved to the HDD if SSD is the bottleneck (after their parquet mirrors exist)
