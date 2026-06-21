# Detached, session-independent supervisor for the stock_options_flow_v0 pull.
# Launched via Start-Process (NOT a child of the Claude Code shell) so it survives the
# session/app being backgrounded or closed — the root cause of the repeated overnight/away deaths.
# Loops pull_chain (resumes from cache each pass) until a pass completes with err=0, or 40 passes.
$ErrorActionPreference = 'Continue'
Set-Location 'C:\Users\benbr\BacktestStation'
$env:THETA_PORT = '25510'; $env:THETA_TIMEOUT = '120'; $env:THETA_RETRIES = '2'
$py = 'C:\Users\benbr\BacktestStation\backend\.venv\Scripts\python.exe'
$names = 'SOFI,AFRM,RIOT,ROKU,DKNG,PLTR,MARA,SIVB,MSTR'
$log = 'C:\Users\benbr\BacktestStation\experiments\stock_options_flow_v0\out\pull_watchdog.log'
New-Item -ItemType Directory -Force -Path (Split-Path $log) | Out-Null
"=== WATCHDOG START $(Get-Date -f 'yyyy-MM-dd HH:mm:ss') (detached, session-independent) ===" | Out-File -Append -Encoding utf8 $log
for ($i = 1; $i -le 40; $i++) {
  "$(Get-Date -f 'HH:mm:ss') --- pass $i begin (you should see [NAME] x/43 lines below) ---" | Tee-Object -FilePath $log -Append
  & $py -u experiments\stock_options_flow_v0\pull_chain.py $names 2023-01-01 2026-06-30 2>&1 | Tee-Object -FilePath $log -Append
  $tail = Get-Content $log -Tail 6 -ErrorAction SilentlyContinue
  if ($tail -match 'DONE.*err=0(\s|$)') {
    "$(Get-Date -f 'HH:mm:ss') === COMPLETE (err=0) after pass $i ===" | Out-File -Append -Encoding utf8 $log
    break
  }
  "$(Get-Date -f 'HH:mm:ss') --- pass $i ended incomplete; resume in 30s ---" | Out-File -Append -Encoding utf8 $log
  Start-Sleep -Seconds 30
}
"=== WATCHDOG EXIT $(Get-Date -f 'HH:mm:ss') ===" | Out-File -Append -Encoding utf8 $log
