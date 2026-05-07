# Warehouse sync prompt for ben-247

Goal: nightly mirror of new parquet partitions from ben-247 → benpc so
the BacktestStation trade-replay UI on benpc has data for recent dates.

**Prerequisite (one-time, on benpc):** SMB share enabled on `D:\data`
as `\\benpc\data` with read/write for the local benbr account. If
`Test-NetConnection benpc -Port 445` from ben-247 fails, stop and tell
Ben to enable SMB first (Settings → Network & Internet → Advanced
sharing → ensure "Network discovery" + "File and printer sharing" are
ON for Private; right-click `D:\data` → Properties → Sharing → Advanced
Sharing → Share this folder → name "data" → Permissions → Everyone
read/write → OK).

---

```
Set up the daily warehouse sync from ben-247 to benpc. Today is
2026-05-06.

Background: parquet_mirror on ben-247 now writes continuous-symbol
partitions (NQ.c.0, ES.c.0, etc) under D:\data\raw\databento\
(commit bfbe738). Daily Databento historical pull writes to the same
tree. benpc's BacktestStation UI reads from its own D:\data\... but
that's nearly empty — we need a nightly sync to mirror ben-247's tree
over there so the replay UI has fresh dates.

Three steps.

1. SMB REACHABILITY TEST. Before doing anything else:
     Test-NetConnection benpc -Port 445
   Must return TcpTestSucceeded: True. If False, stop and report —
   Ben has to enable SMB sharing on benpc (D:\data → \\benpc\data
   share). Don't try other sync methods; SMB is the chosen path.

   Also test the share itself:
     Test-Path \\benpc\data\raw\databento
   If that fails, the share exists but the path doesn't — Ben needs
   to create D:\data\raw\databento on benpc OR adjust permissions.

2. ONE-OFF MANUAL SYNC. Get benpc current right now, then we can
   schedule the recurring task. New PowerShell:

     New-Item -ItemType Directory -Force -Path D:\data\logs | Out-Null
     robocopy D:\data\raw\databento\tbbo \\benpc\data\raw\databento\tbbo /MIR /XO /R:2 /W:5 /LOG+:D:\data\logs\warehouse_sync.log
     robocopy D:\data\raw\databento\mbp-1 \\benpc\data\raw\databento\mbp-1 /MIR /XO /R:2 /W:5 /LOG+:D:\data\logs\warehouse_sync.log

   Flags: /MIR mirrors directory tree; /XO skips files with same/newer
   timestamp on dest (idempotent — only new partitions copy); /R:2 /W:5
   = 2 retries, 5s wait, so a transient network blip doesn't hang.
   /LOG+ appends so you keep a history.

   Report: total files copied, total bytes, any errors.

3. SCHEDULED TASK. Daily at 17:30 ET (post-RTH close, pre-overnight).
   Create a wrapper script first so the schtasks command line stays
   readable:

     $ScriptPath = 'C:\Users\benbr\FractalAMD-\production\warehouse_sync.ps1'

     @'
     # Daily warehouse sync: ben-247 → benpc.
     # Idempotent — /XO skips files already mirrored. Logs append.
     $log = 'D:\data\logs\warehouse_sync.log'
     $stamp = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
     "=== run $stamp ===" | Out-File -FilePath $log -Append -Encoding utf8
     robocopy D:\data\raw\databento\tbbo \\benpc\data\raw\databento\tbbo /MIR /XO /R:2 /W:5 /LOG+:$log
     robocopy D:\data\raw\databento\mbp-1 \\benpc\data\raw\databento\mbp-1 /MIR /XO /R:2 /W:5 /LOG+:$log
     '@ | Out-File -FilePath $ScriptPath -Encoding utf8

   Then register the task:

     $action = New-ScheduledTaskAction `
       -Execute 'powershell.exe' `
       -Argument "-NoProfile -ExecutionPolicy Bypass -File $ScriptPath"
     $trigger = New-ScheduledTaskTrigger -Daily -At '5:30 PM'
     $settings = New-ScheduledTaskSettingsSet -StartWhenAvailable `
       -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
     Register-ScheduledTask `
       -TaskName 'BacktestStationWarehouseSync' `
       -Action $action -Trigger $trigger -Settings $settings `
       -Description 'Mirror D:\data\raw\databento partitions to \\benpc\data nightly.' `
       -RunLevel Highest -User 'benbr'

   Verify: schtasks /query /tn BacktestStationWarehouseSync /v /fo LIST | Select-String "Last Run|Next Run|Status"

   Test-fire it once to confirm the wrapper runs cleanly:
     Start-ScheduledTask -TaskName 'BacktestStationWarehouseSync'
   Then check the log a few seconds later:
     Get-Content D:\data\logs\warehouse_sync.log -Tail 30

DO NOT touch:
  - parquet_mirror (it's already correct)
  - ben-247's local D:\data tree
  - the live runner / Pre10LiveRunner service

Final report:
  - Result of Test-NetConnection benpc -Port 445
  - Result of Test-Path \\benpc\data\raw\databento
  - One-off sync output (file count, bytes, errors)
  - Scheduled task creation confirmation
  - Test-fire log tail
```
