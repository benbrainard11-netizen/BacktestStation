# Run scoped intraday pull for ALL index roots, sequentially, 3 self-heal shards each.
# Granular per-(exp,date) files so progress survives the ~hourly terminal wedges.
param(
  [string]$Roots = "NDXP,SPXW,RUTW,DJX",
  [string]$Start = "2025-05-01",
  [string]$End   = "2026-06-30"
)
$py = "C:\Users\benbr\BacktestStation\backend\.venv\Scripts\python.exe"
$pull = "C:\Users\benbr\BacktestStation\experiments\options_signals_v0\scoped_intraday_pull.py"
$logdir = "C:\Users\benbr\BacktestStation\experiments\options_signals_v0\out\_shards"

foreach ($r in $Roots.Split(",")) {
  Write-Output "=== $r START $(Get-Date -Format 'HH:mm') ==="
  0..2 | ForEach-Object {
    $env:THETA_PORT = "$(25510 + $_)"
    Start-Process -FilePath $py -ArgumentList @($pull, $r, $Start, $End, "$_", "3") `
      -RedirectStandardOutput "$logdir\sci_${r}_s$_.log" -RedirectStandardError "$logdir\sci_${r}_s$_.err" -WindowStyle Hidden | Out-Null
  }
  Start-Sleep -Seconds 30
  do {
    Start-Sleep -Seconds 60
    $alive = (Get-CimInstance Win32_Process -Filter "Name='python.exe'" | Where-Object { $_.CommandLine -like '*scoped_intraday_pull*' }).Count
  } while ($alive -gt 0)
  Write-Output "=== $r DONE $(Get-Date -Format 'HH:mm') ==="
}
Write-Output "ALL INTRADAY ROOTS DONE"
