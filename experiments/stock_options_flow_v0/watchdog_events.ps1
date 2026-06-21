# Detached-friendly supervisor for the Step-A targeted event pull. RUN THIS, then MINIMIZE the window
# (do not close it). Shows progress in the console + logs to out/pull_events.log. Auto-resumes on death.
$ErrorActionPreference = 'Continue'
Set-Location 'C:\Users\benbr\BacktestStation'
$env:THETA_PORT = '25510'; $env:THETA_TIMEOUT = '120'; $env:THETA_RETRIES = '2'
$py = 'C:\Users\benbr\BacktestStation\backend\.venv\Scripts\python.exe'
$log = 'C:\Users\benbr\BacktestStation\experiments\stock_options_flow_v0\out\pull_events.log'
New-Item -ItemType Directory -Force -Path (Split-Path $log) | Out-Null
"=== EVENT PULL START $(Get-Date -f 'HH:mm:ss') (minimize this window, do not close) ===" | Tee-Object -FilePath $log -Append
for ($i = 1; $i -le 40; $i++) {
  "$(Get-Date -f 'HH:mm:ss') --- pass $i ---" | Tee-Object -FilePath $log -Append
  & $py -u experiments\stock_options_flow_v0\pull_events.py 30 2>&1 | Tee-Object -FilePath $log -Append
  $tail = Get-Content $log -Tail 6 -ErrorAction SilentlyContinue
  if ($tail -match 'DONE:.*err=0') { "$(Get-Date -f 'HH:mm:ss') === COMPLETE ===" | Tee-Object -FilePath $log -Append; break }
  Start-Sleep -Seconds 30
}
