# NDX parallel keeper: 6 Terminals (ports 25510-25515), 6-way shard of NDX full history.
# Multi-session up to 6 proven 2026-06-13. NDX has NO vendor greeks -> pull RAW prices
# (bulk_hist/option/eod) + OI; greeks (IV->BS gamma) computed by build_walls_ndx.py.
# Robust self-healing per-Terminal puller, 14-day window. Singleton-guarded. ASCII only.
$ErrorActionPreference = 'SilentlyContinue'
$host.UI.RawUI.WindowTitle = 'NDX DOWNLOAD (6x parallel) - leave open'
$me = $PID
# match only a REAL keeper invocation (-File ...robust_keeper_ndx.ps1), NOT a -Command
# launcher whose script text merely mentions the name (that race made the keeper exit instantly)
$dups = Get-CimInstance Win32_Process -Filter "Name='powershell.exe'" | Where-Object { $_.CommandLine -like '*-File*robust_keeper_ndx*' -and $_.CommandLine -notlike '*-Command*' -and $_.ProcessId -ne $me }
if ($dups) { Write-Host 'another NDX keeper running -> exit'; exit }

$py  = 'C:\Users\benbr\BacktestStation\backend\.venv\Scripts\python.exe'
$rp  = 'C:\Users\benbr\BacktestStation\experiments\options_signals_v0\robust_pull.py'
$log = 'C:\Users\benbr\BacktestStation\experiments\options_signals_v0\out\_shards\logs'
$cfgd = 'C:\Users\benbr\ThetaData\ThetaTerminal'
$cache = 'D:\data\raw\thetadata'
$EP = 'bulk_hist/option/eod'
$START = '2018-01-01'; $END = '2026-12-31'
$N = 3   # 6 overwhelmed the account (sustained 6 sessions -> all dropped); 3 is the proven-stable max
$slots = @()
for ($i=0; $i -lt $N; $i++) { $slots += @{port=(25510+$i).ToString(); cfg="$cfgd\config_$i.properties"} }

function JobDone($sh) { $f="$log\robust_ndx_s$sh.log"; return (Test-Path $f) -and (Select-String -Path $f -Pattern "NDX s$sh] DONE" -Quiet) }
function PullerOnPort($p) { (Get-CimInstance Win32_Process -Filter "Name='python.exe'" | Where-Object { $_.CommandLine -like '*robust_pull*' -and $_.CommandLine -like "* $p *" } | Measure-Object).Count -gt 0 }
function CacheCount { (Get-ChildItem $cache -Recurse -File | Measure-Object).Count }

Write-Host '=====================================================' -ForegroundColor Cyan
Write-Host '  NASDAQ (NDX) DOWNLOAD - 6 Terminals, raw prices' -ForegroundColor Cyan
Write-Host '  (greeks computed locally after). Leave open.' -ForegroundColor Cyan
Write-Host '=====================================================' -ForegroundColor Cyan
while ($true) {
  $allDone = $true
  for ($n=0; $n -lt $N; $n++) {
    if (JobDone $n) { continue }
    $allDone = $false
    if (-not (PullerOnPort $slots[$n].port)) {
      $lg="$log\robust_ndx_s$n.log"
      Start-Process -FilePath $py -ArgumentList $rp,'NDX',$START,$END,$slots[$n].port,$slots[$n].cfg,$n,$N,'14',$EP -RedirectStandardOutput $lg -RedirectStandardError "$lg.err" -WindowStyle Hidden
      Write-Host ("{0}  launched NDX shard {1} on port {2}" -f (Get-Date -Format 'HH:mm:ss'), $n, $slots[$n].port) -ForegroundColor Yellow
      Start-Sleep 15
    }
  }
  if ($allDone) { break }
  $running = (0..($N-1) | Where-Object { PullerOnPort $slots[$_].port }).Count
  Write-Host ("{0}  cache={1}  NDX shards running: {2}/{3}" -f (Get-Date -Format 'HH:mm:ss'), (CacheCount), $running, $N) -ForegroundColor Green
  Start-Sleep 60
}
Write-Host ("{0}  NDX RAW DOWNLOAD COMPLETE - run build_walls_ndx.py" -f (Get-Date -Format 'HH:mm:ss')) -ForegroundColor Green
