# Install the BacktestStation live ingester as a Windows service via NSSM.
#
# Run on the 24/7 collection node (currently insyncserver / ben-247) AFTER
# you've already run setup_ingester.ps1 successfully and verified the
# ingester runs interactively.
#
# Why NSSM: Windows' built-in services don't handle Python scripts
# gracefully. NSSM (Non-Sucking Service Manager) wraps any executable as
# a proper service with automatic restart on failure, output redirection,
# and Stop-Service/Start-Service compatibility.
#
# Usage:
#   powershell -ExecutionPolicy Bypass -File scripts\install_ingester_service.ps1
#
# What it does:
#   1. Verifies BS_DATA_ROOT and DATABENTO_API_KEY are set (machine-level
#      so the SYSTEM service account can read them).
#   2. Downloads NSSM if not already on PATH.
#   3. Removes any prior install of the same service (idempotent).
#   4. Registers BacktestStationIngester service pointing at python.exe
#      with -m app.ingest.live, working dir set to backend/.
#   5. Configures auto-restart, log redirection to {DATA_ROOT}/logs/.
#   6. Starts the service.
#
# Tear down with:
#   nssm stop BacktestStationIngester
#   nssm remove BacktestStationIngester confirm

$ErrorActionPreference = "Stop"
$ServiceName = "BacktestStationIngester"
$BackendDir = Resolve-Path (Join-Path $PSScriptRoot "..\backend")

Write-Host ""
Write-Host "BacktestStation ingester service installer" -ForegroundColor Cyan
Write-Host "===========================================" -ForegroundColor Cyan
Write-Host ""

# --- 1. Locate Python ----------------------------------------------------

$pythonExe = $null
$venvPython = Join-Path $BackendDir ".venv\Scripts\python.exe"
if (Test-Path $venvPython) {
    $pythonExe = (Resolve-Path $venvPython).Path
    Write-Host "  using backend venv: $pythonExe"
} else {
    $sysPython = Get-Command python -ErrorAction SilentlyContinue
    if (-not $sysPython) {
        Write-Host "ERROR: no python found (not in PATH, no backend\.venv)." -ForegroundColor Red
        exit 1
    }
    $pythonExe = $sysPython.Source
    Write-Host "  using system python: $pythonExe"
}

# --- 2. Sanity-check env vars at User OR Machine scope ------------------
# NSSM lets us pass env vars to the service explicitly, so we read the
# user-scope vars now and inject them when registering. This sidesteps
# the SYSTEM-account-can't-see-User-vars footgun.

$dataRoot = [Environment]::GetEnvironmentVariable("BS_DATA_ROOT", "User")
if (-not $dataRoot) {
    $dataRoot = [Environment]::GetEnvironmentVariable("BS_DATA_ROOT", "Machine")
}
$apiKey = [Environment]::GetEnvironmentVariable("DATABENTO_API_KEY", "User")
if (-not $apiKey) {
    $apiKey = [Environment]::GetEnvironmentVariable("DATABENTO_API_KEY", "Machine")
}

if (-not $dataRoot) {
    Write-Host "ERROR: BS_DATA_ROOT not set. Run setup_ingester.ps1 first." -ForegroundColor Red
    exit 1
}
if (-not $apiKey) {
    Write-Host "ERROR: DATABENTO_API_KEY not set. Run setup_ingester.ps1 first." -ForegroundColor Red
    exit 1
}
Write-Host "  BS_DATA_ROOT       = $dataRoot"
Write-Host "  DATABENTO_API_KEY  = $($apiKey.Substring(0,8))... (first 8 chars)"

# --- 3. Locate or fetch NSSM --------------------------------------------

$nssmExe = Get-Command nssm -ErrorAction SilentlyContinue
if (-not $nssmExe) {
    Write-Host ""
    Write-Host "NSSM not on PATH. Downloading nssm 2.24..." -ForegroundColor Yellow

    $tmpDir = Join-Path $env:TEMP "nssm-2.24"
    $zipPath = Join-Path $env:TEMP "nssm.zip"
    $url = "https://nssm.cc/release/nssm-2.24.zip"

    try {
        Invoke-WebRequest -Uri $url -OutFile $zipPath -UseBasicParsing
        Expand-Archive -Path $zipPath -DestinationPath $env:TEMP -Force
    } catch {
        Write-Host "ERROR: NSSM download failed: $($_.Exception.Message)" -ForegroundColor Red
        Write-Host "Manually download from https://nssm.cc/download and place nssm.exe on PATH, then re-run." -ForegroundColor Red
        exit 1
    }

    $arch = if ([Environment]::Is64BitOperatingSystem) { "win64" } else { "win32" }
    $nssmPath = Join-Path $tmpDir "$arch\nssm.exe"
    if (-not (Test-Path $nssmPath)) {
        Write-Host "ERROR: NSSM extracted but nssm.exe not found at $nssmPath" -ForegroundColor Red
        exit 1
    }
    # Copy to a stable location so the service has a fixed exe path.
    $stableNssm = Join-Path $env:ProgramFiles "nssm\nssm.exe"
    New-Item -ItemType Directory -Path (Split-Path $stableNssm) -Force | Out-Null
    Copy-Item $nssmPath $stableNssm -Force
    $nssmExePath = $stableNssm
    Write-Host "  installed nssm to: $stableNssm"
} else {
    $nssmExePath = $nssmExe.Source
    Write-Host "  using existing nssm: $nssmExePath"
}

# --- 4. Remove any prior install ----------------------------------------

$existing = & $nssmExePath status $ServiceName 2>$null
if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "Existing $ServiceName service found, removing..." -ForegroundColor Yellow
    & $nssmExePath stop $ServiceName 2>$null | Out-Null
    & $nssmExePath remove $ServiceName confirm | Out-Null
    Start-Sleep -Seconds 2
}

# --- 5. Install + configure ---------------------------------------------

Write-Host ""
Write-Host "Installing $ServiceName service..." -ForegroundColor Cyan

& $nssmExePath install $ServiceName $pythonExe "-m" "app.ingest.live" | Out-Null
& $nssmExePath set $ServiceName AppDirectory $BackendDir | Out-Null

# Pass env vars to the service. NSSM accepts NAME=value pairs separated
# by `\0` (null bytes) but the simpler interface is one key per call.
& $nssmExePath set $ServiceName AppEnvironmentExtra "BS_DATA_ROOT=$dataRoot" "DATABENTO_API_KEY=$apiKey" | Out-Null

# Auto-restart on failure with backoff.
& $nssmExePath set $ServiceName AppExit Default Restart | Out-Null
& $nssmExePath set $ServiceName AppRestartDelay 30000 | Out-Null

# Redirect stdout/stderr to log files in the warehouse.
$logDir = Join-Path $dataRoot "logs"
New-Item -ItemType Directory -Path $logDir -Force | Out-Null
& $nssmExePath set $ServiceName AppStdout (Join-Path $logDir "live_ingester.service.out.log") | Out-Null
& $nssmExePath set $ServiceName AppStderr (Join-Path $logDir "live_ingester.service.err.log") | Out-Null
& $nssmExePath set $ServiceName AppRotateFiles 1 | Out-Null
& $nssmExePath set $ServiceName AppRotateBytes 10485760 | Out-Null  # 10 MB

# Description.
& $nssmExePath set $ServiceName Description "BacktestStation Databento Live TBBO ingester" | Out-Null

# Auto-start at boot.
& $nssmExePath set $ServiceName Start SERVICE_AUTO_START | Out-Null

# --- 6. Start it --------------------------------------------------------

Write-Host ""
Write-Host "Starting $ServiceName..." -ForegroundColor Cyan
& $nssmExePath start $ServiceName | Out-Null
Start-Sleep -Seconds 3
$status = & $nssmExePath status $ServiceName

Write-Host ""
if ($status -match "RUNNING") {
    Write-Host "Service installed and running." -ForegroundColor Green
    Write-Host ""
    Write-Host "  Status:    $status"
    Write-Host "  Heartbeat: $dataRoot\heartbeat\live_ingester.json"
    Write-Host "  Logs:      $logDir\live_ingester.service.out.log"
    Write-Host "             $logDir\live_ingester.service.err.log"
    Write-Host "             $logDir\live_ingester.log  (the app's own log)"
    Write-Host ""
    Write-Host "Manage with:"
    Write-Host "  nssm status $ServiceName"
    Write-Host "  nssm stop   $ServiceName"
    Write-Host "  nssm start  $ServiceName"
    Write-Host "  nssm remove $ServiceName confirm   # uninstall"
} else {
    Write-Host "Service installed but did not enter RUNNING state." -ForegroundColor Yellow
    Write-Host "  Current status: $status"
    Write-Host "  Check logs:     $logDir\live_ingester.service.err.log"
    Write-Host "  Service-side debug: nssm dump $ServiceName"
    exit 1
}
