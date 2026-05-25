# Install the daily local-MBO-to-R2 mirror task.
#
# This task does NOT call Databento. It only validates local MBO parquet under
# BS_DATA_ROOT and uploads schema=mbo to R2 with inventory merge semantics.
#
# Usage:
#   powershell -ExecutionPolicy Bypass -File scripts\install_mbo_r2_mirror_task.ps1
#   powershell -ExecutionPolicy Bypass -File scripts\install_mbo_r2_mirror_task.ps1 -At 19:15

param(
    [string]$At = "19:15"
)

$ErrorActionPreference = "Stop"

$TaskName = "BacktestStationMboR2Mirror"
$BackendDir = Resolve-Path (Join-Path $PSScriptRoot "..\backend")
$RunnerScript = Resolve-Path (Join-Path $PSScriptRoot "run_mbo_r2_mirror.ps1")
$User = "$env:USERDOMAIN\$env:USERNAME"

Write-Host ""
Write-Host "BacktestStation MBO R2 mirror task installer" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan

$venvPython = Join-Path $BackendDir ".venv\Scripts\python.exe"
if (Test-Path $venvPython) {
    $PythonExe = (Resolve-Path $venvPython).Path
} else {
    $cmd = Get-Command python -ErrorAction SilentlyContinue
    if (-not $cmd) {
        Write-Host "ERROR: no python found." -ForegroundColor Red
        exit 1
    }
    $PythonExe = $cmd.Source
}

Write-Host "  python      = $PythonExe"
Write-Host "  backend dir = $BackendDir"
Write-Host "  user        = $User"
Write-Host "  task time   = $At local"

function Test-EnvVarPresent {
    param([string]$Name)

    $userValue = [Environment]::GetEnvironmentVariable($Name, "User")
    $machineValue = [Environment]::GetEnvironmentVariable($Name, "Machine")
    if (-not $userValue -and -not $machineValue) {
        Write-Host "ERROR: $Name is not set at User or Machine scope." -ForegroundColor Red
        exit 1
    }
}

function Test-TaskRegistered {
    param([string]$Name)

    if (Get-ScheduledTask -TaskName $Name -ErrorAction SilentlyContinue) {
        return $true
    }

    $systemRoot = $env:SystemRoot
    if (-not $systemRoot) {
        $systemRoot = "C:\Windows"
    }
    $taskFile = Join-Path $systemRoot ("System32\Tasks\" + $Name.TrimStart("\"))
    return Test-Path -LiteralPath $taskFile
}

Test-EnvVarPresent "BS_DATA_ROOT"
Test-EnvVarPresent "BS_R2_BUCKET"
Test-EnvVarPresent "BS_R2_ENDPOINT"
Test-EnvVarPresent "BS_R2_ACCESS_KEY"
Test-EnvVarPresent "BS_R2_SECRET"

& $PythonExe -c "import boto3, pyarrow" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: boto3 and pyarrow must be importable from $PythonExe." -ForegroundColor Red
    exit 1
}

$action = New-ScheduledTaskAction `
    -Execute $PythonExe `
    -Argument "-m app.ingest.mbo_r2_mirror" `
    -WorkingDirectory $BackendDir

$trigger = New-ScheduledTaskTrigger -Daily -At (Get-Date $At)

$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -RunOnlyIfNetworkAvailable `
    -ExecutionTimeLimit (New-TimeSpan -Hours 4) `
    -MultipleInstances IgnoreNew

$principal = New-ScheduledTaskPrincipal `
    -UserId $User `
    -LogonType S4U `
    -RunLevel Limited

try {
    Register-ScheduledTask `
        -TaskName $TaskName `
        -Description "Validate local MBO parquet and mirror schema=mbo to Cloudflare R2. Does not call Databento." `
        -Action $action `
        -Trigger $trigger `
        -Settings $settings `
        -Principal $principal `
        -Force | Out-Null
} catch {
    Write-Host "Register-ScheduledTask failed: $($_.Exception.Message)" -ForegroundColor Yellow
    Write-Host "Falling back to schtasks current-user registration." -ForegroundColor Yellow
    Write-Host "Fallback tasks run when the user is logged on; use an elevated shell for S4U/background registration." -ForegroundColor Yellow

    $tr = "powershell.exe -NoProfile -ExecutionPolicy Bypass -File `"$RunnerScript`""
    & schtasks.exe /Create /TN $TaskName /SC DAILY /ST $At /TR $tr /F | Out-Host
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: schtasks fallback failed with exit code $LASTEXITCODE." -ForegroundColor Red
        exit $LASTEXITCODE
    }
}

if (-not (Test-TaskRegistered $TaskName)) {
    Write-Host "ERROR: $TaskName did not register. See errors above." -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "Installed $TaskName." -ForegroundColor Green
Write-Host ""
Write-Host "Verify:"
Write-Host "  Get-ScheduledTask -TaskName $TaskName"
Write-Host ""
Write-Host "Run on demand:"
Write-Host "  Start-ScheduledTask -TaskName $TaskName"
Write-Host ""
Write-Host "Logs:"
Write-Host "  `$env:BS_DATA_ROOT\logs\mbo_r2_mirror.log"
Write-Host "  `$env:BS_DATA_ROOT\logs\mbo_r2_mirror_runs.json"
