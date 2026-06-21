# Check-and-revive for the options archive pull. Run by Windows Task Scheduler every 15 min.
# If the cache is fresh (<15 min), do nothing. Otherwise: kill shard procs, bounce Terminal,
# relaunch the canonical 5-stream fleet. Stops itself once all SPX shard parquets exist.
$ErrorActionPreference = 'SilentlyContinue'
$pat = 'gex_' + 'shard'
$py = 'C:\Users\benbr\BacktestStation\backend\.venv\Scripts\python.exe'
$gs = 'C:\Users\benbr\BacktestStation\experiments\options_signals_v0\gex_shard.py'
$t = 'C:\Users\benbr\BacktestStation\experiments\options_signals_v0\theta'
$shards = 'C:\Users\benbr\BacktestStation\experiments\options_signals_v0\out\_shards'
$log = "$shards\logs"
New-Item -ItemType Directory -Force $log | Out-Null
$stamp = Get-Date -Format 'MM-dd HH:mm'

# done? (3 SPX shard parquets present)
$spxDone = (Get-ChildItem $shards -Filter 'spx_s*.parquet' | Where-Object { $_.Name -notlike '*spot*' } | Measure-Object).Count
if ($spxDone -ge 3) { Add-Content "$log\revive.log" "$stamp SPX complete; revive idle"; exit 0 }

# fresh? (any cache file newer than 15 min)
$newest = (Get-ChildItem D:\data\raw\thetadata -Recurse -File | Sort-Object LastWriteTime -Descending | Select-Object -First 1).LastWriteTime
if ($newest -gt (Get-Date).AddMinutes(-30)) { Add-Content "$log\revive.log" "$stamp fresh ($newest); ok"; exit 0 }

# Is the Terminal actually SERVING? A hung java process makes pullers look alive-but-idle and the
# young-puller grace below would shield it forever. Health-check the HTTP endpoint first.
# 60s timeout: the Terminal serves list/expirations in ~40s (large chains, slow backend) — an
# 8s timeout gave FALSE "down" and bounced a WORKING terminal all night (06-12/13 death spiral).
$termOk = $false
try { $termOk = (Invoke-WebRequest -Uri "http://127.0.0.1:25510/v2/list/expirations?root=SPXW" -TimeoutSec 60 -UseBasicParsing).StatusCode -eq 200 } catch { $termOk = $false }

# warming up? (pullers fast-forward through cached expirations before producing NEW files —
# 15-25 min; early kill caused reset loops) -> grace ONLY while the Terminal is genuinely serving
$young = Get-CimInstance Win32_Process -Filter "Name='python.exe'" | Where-Object {
    $_.CommandLine -like "*$pat*" -and $_.CreationDate -gt (Get-Date).AddMinutes(-30) }
if ($termOk -and ($young | Measure-Object).Count -gt 0) { Add-Content "$log\revive.log" "$stamp stale, Terminal OK, $((($young | Measure-Object).Count)) young pullers warming up; waiting"; exit 0 }
if (-not $termOk) { Add-Content "$log\revive.log" "$stamp Terminal HUNG -> force bounce" }

# LOW CONCURRENCY: the local Theta Terminal HANGS under heavy parallelism (12 pullers killed it
# repeatedly 6/12). Two streams max — slower but the Terminal survives, so it actually progresses.
# Kill-first (incl powershell chain wrappers) so duplicates can NEVER accumulate.
Add-Content "$log\revive.log" "$stamp STALE (newest $newest) -> reviving (2-stream)"
Get-CimInstance Win32_Process -Filter "Name='python.exe'" | Where-Object { $_.CommandLine -like "*$pat*" } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -Confirm:$false }
Get-CimInstance Win32_Process -Filter "Name='powershell.exe'" | Where-Object { $_.CommandLine -like "*$pat*" -and $_.ProcessId -ne $PID } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -Confirm:$false }
Get-Process java | Stop-Process -Force -Confirm:$false
Start-Sleep -Seconds 6
Start-Process -FilePath "C:\Program Files\Microsoft\jdk-21.0.11.10-hotspot\bin\java.exe" -ArgumentList '-jar',"$t\ThetaTerminal.jar",'--creds-file',"$t\creds.txt" -WorkingDirectory $t -WindowStyle Hidden
Start-Sleep -Seconds 50  # Terminal needs ~45s for full MDDS/FPSS remote login before it serves
# ONE STREAM, concurrency=2 (the config that ran stably all morning 6/12). The Terminal CRASHES
# (java exits, OOM-suspected) under more load — stability > speed for unattended overnight. One
# stream does ALL roots sequentially: SPX, then small roots. Slow but it STAYS UP and progresses.
$a = "& '$py' '$gs' SPX 2017-01-01 2026-06-10 0 1 *> '$log\spx0.log'; & '$py' '$gs' RUT 2017-01-01 2026-06-10 0 1 *> '$log\rut.log'; & '$py' '$gs' DJX 2017-01-01 2026-06-10 0 1 *> '$log\djx.log'; & '$py' '$gs' NDX 2017-01-01 2026-06-10 0 1 *> '$log\ndx.log'; & '$py' '$gs' GLD 2017-01-01 2026-06-10 0 1 *> '$log\gld.log'; & '$py' '$gs' SLV 2017-01-01 2026-06-10 0 1 *> '$log\slv.log'"
Start-Process powershell -ArgumentList '-NoProfile','-Command',$a -WindowStyle Hidden
Add-Content "$log\revive.log" "$stamp 1-stream relaunched (concurrency=2, stability mode)"
