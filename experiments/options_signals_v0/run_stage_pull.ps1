# Sequential multi-root option pull driver: for each root, launch 3 shards across the 3 Terminals
# (each shard owns one config so restarts don't collide), wait for all 3 DONE, then next root.
# Stays within the proven 3-session ceiling. Reusable for EOD (eod_greeks) and intraday (greeks+ivl).
#
# Usage:
#   EOD:      run_stage_pull.ps1 -Roots NVDA,AAPL,MSFT,TSLA -Start 2023-01-01 -End 2026-12-31 -Window 35 -Ep bulk_hist/option/eod_greeks -Tag opt
#   intraday: run_stage_pull.ps1 -Roots NVDA,AAPL,MSFT,TSLA,NDX -Window 14 -Ep bulk_hist/option/greeks -Ivl 300000 -Tag intra
param(
  [string]$Roots = "NVDA,AAPL,MSFT,TSLA",
  [string]$Start = "2023-01-01",
  [string]$End   = "2026-12-31",
  [int]$Window   = 35,
  [string]$Ep    = "bulk_hist/option/eod_greeks",
  [int]$Ivl      = 0,
  [string]$Tag   = "opt"
)
$py = "C:\Users\benbr\BacktestStation\backend\.venv\Scripts\python.exe"
$rp = "C:\Users\benbr\BacktestStation\experiments\options_signals_v0\robust_pull.py"
$cfgdir = "C:\Users\benbr\ThetaData\ThetaTerminal"
$logdir = "C:\Users\benbr\BacktestStation\experiments\options_signals_v0\out\_shards"
New-Item -ItemType Directory -Force $logdir | Out-Null

foreach ($t in $Roots.Split(",")) {
  Write-Output "=== $Tag $t START $(Get-Date -Format 'HH:mm') (win=$Window ivl=$Ivl) ==="
  0..2 | ForEach-Object {
    $port = 25510 + $_
    $cfg  = "$cfgdir\config_$_.properties"
    $log  = "$logdir\${Tag}_${t}_s$_.log"
    Start-Process -FilePath $py -ArgumentList @($rp, $t, $Start, $End, "$port", $cfg, "$_", "3", "$Window", $Ep, "$Ivl") `
      -RedirectStandardOutput $log -RedirectStandardError "$log.err" -WindowStyle Hidden | Out-Null
  }
  $waited = 0
  do {
    Start-Sleep -Seconds 30; $waited += 30
    $done = (Get-ChildItem "$logdir\${Tag}_${t}_s*.log" -ErrorAction SilentlyContinue | Select-String -Pattern "DONE" -List).Count
  } while ($done -lt 3 -and $waited -lt 21600)
  $poison = (Get-ChildItem "$logdir\${Tag}_${t}_s*.log" -ErrorAction SilentlyContinue | Select-String -Pattern "POISON").Count
  Write-Output "=== $Tag $t DONE=$done/3 poison=$poison after $([int]($waited/60))min ==="
}
Write-Output "ALL $Tag ROOTS COMPLETE"
