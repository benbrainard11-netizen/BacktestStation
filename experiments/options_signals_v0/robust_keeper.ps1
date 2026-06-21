# Parallel keeper: 3 Terminals (ports 25510/11/12, configs 0/1/2), proven multi-session.
# PHASE 1: split the SPX gap 3 ways (one shard per Terminal) -> ~3x faster on the bottleneck.
# PHASE 2: RUT + DJX in parallel on two of the Terminals.
# Each puller (robust_pull) manages its OWN Terminal (restart-on-freeze, matched by config
# name) and skips poison expirations. Keeper just keeps pullers alive + advances phases.
# Singleton-guarded. NDX skipped (vendor has no greeks). ASCII only.
$ErrorActionPreference = 'SilentlyContinue'
$host.UI.RawUI.WindowTitle = 'OPTIONS PARALLEL KEEPER (3x) - leave open'
$me = $PID
$dups = Get-CimInstance Win32_Process -Filter "Name='powershell.exe'" | Where-Object { $_.CommandLine -like '*robust_keeper*' -and $_.ProcessId -ne $me }
if ($dups) { Write-Host 'another keeper running -> exit'; exit }

$py  = 'C:\Users\benbr\BacktestStation\backend\.venv\Scripts\python.exe'
$rp  = 'C:\Users\benbr\BacktestStation\experiments\options_signals_v0\robust_pull.py'
$log = 'C:\Users\benbr\BacktestStation\experiments\options_signals_v0\out\_shards\logs'
$cfgd = 'C:\Users\benbr\ThetaData\ThetaTerminal'
$cache = 'D:\data\raw\thetadata'
$slots = @(
  @{port='25510'; cfg="$cfgd\config_0.properties"},
  @{port='25511'; cfg="$cfgd\config_1.properties"},
  @{port='25512'; cfg="$cfgd\config_2.properties"}
)
$spxStart='2021-01-01'; $spxEnd='2023-05-31'

function JobDone($idx,$sh) { $f="$log\robust_$($idx.ToLower())_s$sh.log"; return (Test-Path $f) -and (Select-String -Path $f -Pattern "$idx s$sh] DONE" -Quiet) }
function PullerOnPort($p) { (Get-CimInstance Win32_Process -Filter "Name='python.exe'" | Where-Object { $_.CommandLine -like '*robust_pull*' -and $_.CommandLine -like "* $p *" } | Measure-Object).Count -gt 0 }
function Launch($idx,$st,$en,$slot,$sh,$ns) {
  $lg="$log\robust_$($idx.ToLower())_s$sh.log"
  Start-Process -FilePath $py -ArgumentList $rp,$idx,$st,$en,$slot.port,$slot.cfg,$sh,$ns,'14' -RedirectStandardOutput $lg -RedirectStandardError "$lg.err" -WindowStyle Hidden
}
function CacheCount { (Get-ChildItem $cache -Recurse -File | Measure-Object).Count }

Write-Host '=====================================================' -ForegroundColor Cyan
Write-Host '  OPTIONS PARALLEL DOWNLOAD - 3 Terminals, ~3x' -ForegroundColor Cyan
Write-Host '  Phase 1: SPX gap split 3 ways. Phase 2: RUT + DJX.' -ForegroundColor Cyan
Write-Host '  Self-healing, hands-off. Leave open.' -ForegroundColor Cyan
Write-Host '=====================================================' -ForegroundColor Cyan

Write-Host ("{0}  PHASE 1: SPX gap, 3-way parallel" -f (Get-Date -Format 'HH:mm:ss')) -ForegroundColor Yellow
while ($true) {
  $allDone = $true
  for ($n=0; $n -lt 3; $n++) {
    if (JobDone 'SPX' $n) { continue }
    $allDone = $false
    if (-not (PullerOnPort $slots[$n].port)) {
      Launch 'SPX' $spxStart $spxEnd $slots[$n] $n 3
      Write-Host ("{0}  launched SPX shard {1} on port {2}" -f (Get-Date -Format 'HH:mm:ss'), $n, $slots[$n].port) -ForegroundColor Yellow
      Start-Sleep 20   # stagger Terminal logins
    }
  }
  if ($allDone) { break }
  Write-Host ("{0}  cache={1}  SPX shards running: {2}/3" -f (Get-Date -Format 'HH:mm:ss'), (CacheCount), (@(0,1,2 | Where-Object { PullerOnPort $slots[$_].port }).Count)) -ForegroundColor Green
  Start-Sleep 60
}
Write-Host ("{0}  SPX GAP COMPLETE" -f (Get-Date -Format 'HH:mm:ss')) -ForegroundColor Green

Write-Host ("{0}  PHASE 2: RUT + DJX in parallel" -f (Get-Date -Format 'HH:mm:ss')) -ForegroundColor Yellow
$after = @( @{idx='RUT'; slot=0}, @{idx='DJX'; slot=1} )
while ($true) {
  $allDone = $true
  foreach ($j in $after) {
    if (JobDone $j.idx 0) { continue }
    $allDone = $false
    $sl = $slots[$j.slot]
    if (-not (PullerOnPort $sl.port)) {
      Launch $j.idx '2024-06-01' '2026-06-10' $sl 0 1
      Write-Host ("{0}  launched {1} on port {2}" -f (Get-Date -Format 'HH:mm:ss'), $j.idx, $sl.port) -ForegroundColor Yellow
      Start-Sleep 15
    }
  }
  if ($allDone) { break }
  Write-Host ("{0}  cache={1}  phase2 running" -f (Get-Date -Format 'HH:mm:ss'), (CacheCount)) -ForegroundColor Green
  Start-Sleep 60
}
Write-Host ("{0}  ALL DONE - options download complete" -f (Get-Date -Format 'HH:mm:ss')) -ForegroundColor Green
