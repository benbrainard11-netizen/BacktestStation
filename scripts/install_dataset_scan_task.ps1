# Register only the daily BacktestStation dataset-registry scan task.
#
# This task runs:
#   python -m app.cli.scan_datasets
#
# It refreshes data/meta.sqlite from BS_DATA_ROOT so /data-health coverage
# and readiness are based on current warehouse files even when the FastAPI
# server has not been opened.
#
# Usage:
#   powershell -ExecutionPolicy Bypass -File scripts\install_dataset_scan_task.ps1
#
# Tear down:
#   Unregister-ScheduledTask -TaskName BacktestStationDatasetScan -Confirm:$false

$ErrorActionPreference = "Stop"

$BackendDir = Resolve-Path (Join-Path $PSScriptRoot "..\backend")
$User       = "$env:USERDOMAIN\$env:USERNAME"

Write-Host ""
Write-Host "BacktestStation dataset scan task installer" -ForegroundColor Cyan
Write-Host "===========================================" -ForegroundColor Cyan
Write-Host ""

$venvPython = Join-Path $BackendDir ".venv\Scripts\python.exe"
if (Test-Path $venvPython) {
    $pythonExe = (Resolve-Path $venvPython).Path
    Write-Host "  using backend venv: $pythonExe"
} else {
    $sysPython = Get-Command python -ErrorAction SilentlyContinue
    if (-not $sysPython) {
        Write-Host "ERROR: no python found." -ForegroundColor Red
        exit 1
    }
    $pythonExe = $sysPython.Source
    Write-Host "  using system python: $pythonExe"
}

$dataRoot = [Environment]::GetEnvironmentVariable("BS_DATA_ROOT", "User")
if (-not $dataRoot) {
    Write-Host "ERROR: BS_DATA_ROOT not set at User scope. The scheduled task will not know what warehouse to scan." -ForegroundColor Red
    exit 1
}
Write-Host "  BS_DATA_ROOT = $dataRoot"
Write-Host "  user         = $User"

Write-Host ""
Write-Host "Checking scanner CLI..." -ForegroundColor Yellow
& $pythonExe -m app.cli.scan_datasets --help *> $null
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: app.cli.scan_datasets is not runnable from $pythonExe." -ForegroundColor Red
    exit 1
}
Write-Host "  scanner CLI OK"

Write-Host ""
Write-Host "Registering BacktestStationDatasetScan (daily at 04:30)..." -ForegroundColor Cyan

$action = New-ScheduledTaskAction `
    -Execute $pythonExe `
    -Argument '-m app.cli.scan_datasets' `
    -WorkingDirectory $BackendDir

$trigger = New-ScheduledTaskTrigger `
    -Daily `
    -At (Get-Date '04:30:00')

$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -ExecutionTimeLimit (New-TimeSpan -Hours 1) `
    -MultipleInstances IgnoreNew

$principal = New-ScheduledTaskPrincipal `
    -UserId $User `
    -LogonType S4U `
    -RunLevel Limited

Register-ScheduledTask `
    -TaskName 'BacktestStationDatasetScan' `
    -Description 'Refresh BacktestStation datasets registry from BS_DATA_ROOT daily' `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Principal $principal `
    -Force | Out-Null

if (-not (Get-ScheduledTask -TaskName 'BacktestStationDatasetScan' -ErrorAction SilentlyContinue)) {
    Write-Host "ERROR: BacktestStationDatasetScan did not register. See errors above." -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "Done." -ForegroundColor Green
Get-ScheduledTask -TaskName 'BacktestStationDatasetScan' | `
    Select-Object TaskName, State, `
        @{n='NextRun';e={(Get-ScheduledTaskInfo $_).NextRunTime}} | `
    Format-Table -AutoSize | Out-String -Width 200

Write-Host "Manage:"
Write-Host "  Start-ScheduledTask BacktestStationDatasetScan"
Write-Host "  Get-ScheduledTaskInfo BacktestStationDatasetScan"
Write-Host "  Get-Content `$env:BS_DATA_ROOT\logs\dataset_scan.log -Tail 50"
Write-Host ""
