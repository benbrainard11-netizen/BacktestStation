# STABLE single-stream options puller + watchdog. Replaces pull_console + revive_pulls.
# Findings 2026-06-13 (diag_vendor_gap.py): SPX has data ALL years (incl the 2021-22 "gap");
# NDX is 100% NO_DATA and FREEZES the Terminal -> NDX is SKIPPED. Root cause of the days-long
# stall: 3-4 PARALLEL streams + feeding NO_DATA crashed the flaky Terminal, and the old reviver
# "recovered" by relaunching the same parallel fleet. This runs ONE stream and restarts ONLY
# the Terminal when it actually freezes, using CACHE GROWTH as the liveness signal. ASCII only.
$ErrorActionPreference = 'SilentlyContinue'
$host.UI.RawUI.WindowTitle = 'OPTIONS DOWNLOAD (stable) - leave open'
$py    = 'C:\Users\benbr\BacktestStation\backend\.venv\Scripts\python.exe'
$gs    = 'C:\Users\benbr\BacktestStation\experiments\options_signals_v0\gex_shard.py'
$jar   = 'C:\Users\benbr\BacktestStation\experiments\options_signals_v0\theta\ThetaTerminal.jar'
$creds = 'C:\Users\benbr\BacktestStation\experiments\options_signals_v0\theta\creds.txt'
$tdir  = 'C:\Users\benbr\BacktestStation\experiments\options_signals_v0\theta'
$java  = 'C:\Program Files\Microsoft\jdk-21.0.11.10-hotspot\bin\java.exe'
$log   = 'C:\Users\benbr\BacktestStation\experiments\options_signals_v0\out\_shards\logs'
$cache = 'D:\data\raw\thetadata'
New-Item -ItemType Directory -Force $log | Out-Null

function Test-Term { try { return ((Invoke-WebRequest 'http://127.0.0.1:25510/v2/list/expirations?root=SPXW' -TimeoutSec 8 -UseBasicParsing).StatusCode -eq 200) } catch { return $false } }
function Kill-Term { Get-CimInstance Win32_Process -Filter "Name='java.exe'" | Where-Object { $_.CommandLine -like '*ThetaTerminal*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force } }
function Start-Term {
  Kill-Term; Start-Sleep 4
  Start-Process -FilePath $java -ArgumentList '-jar',$jar,'--creds-file',$creds -WorkingDirectory $tdir -WindowStyle Hidden
  for ($i=0; $i -lt 24; $i++) { Start-Sleep 5; if (Test-Term) { return $true } }
  return $false
}
function Puller-Count { (Get-CimInstance Win32_Process -Filter "Name='python.exe'" | Where-Object { $_.CommandLine -like '*gex_shard*' } | Measure-Object).Count }
function Kill-Puller { Get-CimInstance Win32_Process -Filter "Name='python.exe'" | Where-Object { $_.CommandLine -like '*gex_shard*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }; Get-CimInstance Win32_Process -Filter "Name='powershell.exe'" | Where-Object { $_.CommandLine -like '*gex_shard*' -and $_.ProcessId -ne $PID } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force } }
function Start-Puller {
  # ONE stream, 35-DAY windows (light enough that the flaky Terminal serves them without
  # dead-stalling; the 100-day window froze it solid). NDX skipped (100% NO_DATA). Order:
  # SPX 2021-22 GAP first (the valuable missing piece), then recent RUT + DJX. Resumable
  # via theta_store cache, so a restart never loses finished work.
  $chain = "& '$py' '$gs' SPX 2021-01-01 2023-05-31 0 1 35 *> '$log\stable_spx.log'; " +
           "& '$py' '$gs' RUT 2024-06-01 2026-06-10 0 1 35 *> '$log\stable_rut.log'; " +
           "& '$py' '$gs' DJX 2024-06-01 2026-06-10 0 1 35 *> '$log\stable_djx.log'"
  Start-Process powershell -ArgumentList '-NoProfile','-Command',$chain -WindowStyle Hidden
}
function Cache-AgeMin {
  $f = Get-ChildItem $cache -Recurse -File | Sort-Object LastWriteTime -Descending | Select-Object -First 1
  if ($f) { return [Math]::Round(((Get-Date) - $f.LastWriteTime).TotalMinutes, 1) } else { return 999 }
}

Write-Host '=====================================================' -ForegroundColor Cyan
Write-Host '  OPTIONS DOWNLOAD - stable single-stream + watchdog' -ForegroundColor Cyan
Write-Host '  SPX -> RUT -> DJX (NDX skipped: vendor has no data)' -ForegroundColor Cyan
Write-Host '  Restarts ONLY the Terminal when it freezes.' -ForegroundColor Cyan
Write-Host '=====================================================' -ForegroundColor Cyan

if (-not (Test-Term)) { Write-Host 'starting Terminal...' -ForegroundColor Yellow; Start-Term | Out-Null }
$failStreak = 0
$lastFiles = (Get-ChildItem $cache -Recurse -File | Measure-Object).Count
while ($true) {
  $termOk   = Test-Term
  $pullers  = Puller-Count
  $cacheAge = Cache-AgeMin
  $files    = (Get-ChildItem $cache -Recurse -File | Measure-Object).Count
  # STALL = cache hasn't grown in >8 min. CRITICAL: do NOT gate on the list-endpoint probe
  # -- the Terminal's DATA path can wedge (java 0% CPU) while the lightweight list endpoint
  # still answers "ok" (this exact blind spot left it dead 06:37->09:21 undetected). Cache
  # growth is the ONLY trustworthy liveness signal. On stall, restart BOTH Terminal + puller
  # (the puller is hung on a dead socket; restarting the Terminal alone won't free it).
  if ($cacheAge -gt 8) {
    Write-Host ("{0}  STALLED (cache {1}m, term-probe={2}) -> full restart Terminal+puller" -f (Get-Date -Format 'HH:mm:ss'), $cacheAge, (@('frozen','ok')[[int]$termOk])) -ForegroundColor Red
    Kill-Puller
    Start-Term | Out-Null
    Start-Sleep 3
    Start-Puller
  } elseif (($pullers -eq 0) -and $termOk) {
    Write-Host ("{0}  launching single stream" -f (Get-Date -Format 'HH:mm:ss')) -ForegroundColor Yellow
    Start-Puller
  }

  $color = if (-not $termOk) { 'Red' } elseif ($cacheAge -le 5) { 'Green' } else { 'Yellow' }
  Write-Host ("{0}  files={1} (+{2}/cycle)  cache-age={3}m  term={4}  streams={5}" -f `
    (Get-Date -Format 'HH:mm:ss'), $files, ($files-$lastFiles), $cacheAge, (@('FROZEN','ok')[[int]$termOk]), $pullers) -ForegroundColor $color
  $lastFiles = $files
  Start-Sleep -Seconds 45
}
