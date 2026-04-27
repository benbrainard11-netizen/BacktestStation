# Register two daily tasks on ben-247 to close the live-trade pipeline:
#
#   BacktestStationReconcile     -- run reconcile_from_rithmic.py at
#                                   13:30 local Phoenix = 16:30 ET, so
#                                   trades.jsonl is fully reconciled
#                                   against Rithmic fills before being
#                                   shipped to main PC.
#
#   BacktestStationTaildropTrades -- tailscale file cp trades.jsonl to
#                                   benpc at 13:45 local = 16:45 ET,
#                                   15 minutes after reconcile so the
#                                   shipped file is the corrected one.
#
# Both run as the current user via -LogonType S4U so they execute even
# when nobody is logged in AND inherit User-scope env vars (Rithmic
# creds + Tailscale auth).
#
# Times are LOCAL (Phoenix, no DST). 16:30 ET = 13:30 Phoenix during
# US Eastern DST (Mar - Nov). Adjust if the system timezone changes.
#
# Run AFTER setup_ingester.ps1 (so env vars exist). Needs admin.
#
# Usage:
#   powershell -ExecutionPolicy Bypass -File scripts\install_reconcile_taildrop_tasks.ps1
#
# Tear down:
#   Unregister-ScheduledTask -TaskName BacktestStationReconcile      -Confirm:$false
#   Unregister-ScheduledTask -TaskName BacktestStationTaildropTrades -Confirm:$false

$ErrorActionPreference = "Stop"

$User       = "$env:USERDOMAIN\$env:USERNAME"
$PythonExe  = 'C:\Users\benbr\AppData\Local\Programs\Python\Python312\python.exe'
$TailscaleExe = 'C:\Program Files\Tailscale\tailscale.exe'
$BotDir     = 'C:\Users\benbr\FractalAMD-\production'
$TradesFile = Join-Path $BotDir 'trades.jsonl'
$ReconcilePy = Join-Path $BotDir 'reconcile_from_rithmic.py'

Write-Host ""
Write-Host "BacktestStation reconcile + taildrop tasks installer" -ForegroundColor Cyan
Write-Host "=====================================================" -ForegroundColor Cyan
Write-Host ""

# --- 1. Sanity-check paths ----------------------------------------------

foreach ($p in @($PythonExe, $TailscaleExe, $TradesFile, $ReconcilePy)) {
    if (-not (Test-Path $p)) {
        Write-Host "ERROR: missing required path: $p" -ForegroundColor Red
        exit 1
    }
}
Write-Host "  python:    $PythonExe"
Write-Host "  tailscale: $TailscaleExe"
Write-Host "  reconcile: $ReconcilePy"
Write-Host "  trades:    $TradesFile"
Write-Host "  user:      $User"

# --- 2. Shared settings + principal -------------------------------------

$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 15) `
    -MultipleInstances IgnoreNew

$principal = New-ScheduledTaskPrincipal `
    -UserId $User `
    -LogonType S4U `
    -RunLevel Limited

# --- 3. Register reconcile task (daily 13:30 local = 16:30 ET) ---------

Write-Host ""
Write-Host "Registering BacktestStationReconcile (daily 13:30 local / 16:30 ET)..." -ForegroundColor Cyan

$reconcileAction = New-ScheduledTaskAction `
    -Execute $PythonExe `
    -Argument 'reconcile_from_rithmic.py' `
    -WorkingDirectory $BotDir

$reconcileTrigger = New-ScheduledTaskTrigger -Daily -At '13:30'

Register-ScheduledTask `
    -TaskName 'BacktestStationReconcile' `
    -Description 'Reconcile trades.jsonl against Rithmic fills (16:30 ET, before Taildrop)' `
    -Action $reconcileAction `
    -Trigger $reconcileTrigger `
    -Settings $settings `
    -Principal $principal `
    -Force | Out-Null

if (-not (Get-ScheduledTask -TaskName 'BacktestStationReconcile' -ErrorAction SilentlyContinue)) {
    Write-Host "ERROR: BacktestStationReconcile did not register." -ForegroundColor Red
    exit 1
}
Write-Host "  registered."

# --- 4. Register Taildrop task (daily 13:45 local = 16:45 ET) ----------

Write-Host ""
Write-Host "Registering BacktestStationTaildropTrades (daily 13:45 local / 16:45 ET)..." -ForegroundColor Cyan

# tailscale CLI takes positional args; -Argument is one string with all
# of them. The path needs quotes because Windows might split on spaces
# (no spaces in our path, but defensive).
$taildropAction = New-ScheduledTaskAction `
    -Execute $TailscaleExe `
    -Argument ('file cp "{0}" benpc:' -f $TradesFile)

$taildropTrigger = New-ScheduledTaskTrigger -Daily -At '13:45'

Register-ScheduledTask `
    -TaskName 'BacktestStationTaildropTrades' `
    -Description 'Taildrop reconciled trades.jsonl to benpc (16:45 ET, 15min after reconcile)' `
    -Action $taildropAction `
    -Trigger $taildropTrigger `
    -Settings $settings `
    -Principal $principal `
    -Force | Out-Null

if (-not (Get-ScheduledTask -TaskName 'BacktestStationTaildropTrades' -ErrorAction SilentlyContinue)) {
    Write-Host "ERROR: BacktestStationTaildropTrades did not register." -ForegroundColor Red
    exit 1
}
Write-Host "  registered."

# --- 5. Summary ---------------------------------------------------------

Write-Host ""
Write-Host "Done." -ForegroundColor Green
Write-Host ""
Get-ScheduledTask | Where-Object { $_.TaskName -in @('BacktestStationReconcile','BacktestStationTaildropTrades') } | `
    Select-Object TaskName, State, `
        @{n='NextRun';e={(Get-ScheduledTaskInfo $_).NextRunTime}} | `
    Format-Table -AutoSize | Out-String -Width 200

Write-Host "Manage:"
Write-Host "  Get-ScheduledTask -TaskName BacktestStation*    # status"
Write-Host "  Start-ScheduledTask BacktestStationReconcile    # run-now"
Write-Host "  Unregister-ScheduledTask <name> -Confirm:`$false"
Write-Host ""
