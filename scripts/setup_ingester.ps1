# One-time setup for the BacktestStation live data ingester on a
# Windows collection node (ben-247 / husky-247).
#
# - Prompts for the Databento API key with a HIDDEN input box.
# - Sets BS_DATA_ROOT and DATABENTO_API_KEY as User env vars (persist).
# - Creates the data directory tree.
# - Tests that Python + databento can be imported.
#
# Run this ONCE per collection node. The key never echoes to the screen,
# never lands in shell history, never gets pasted into chat.
#
# Usage:
#   cd C:\Users\benbr\BacktestStation\scripts
#   powershell -ExecutionPolicy Bypass -File setup_ingester.ps1

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "BacktestStation ingester setup" -ForegroundColor Cyan
Write-Host "===============================" -ForegroundColor Cyan
Write-Host ""

# --- 1. Data root --------------------------------------------------------

$defaultRoot = if (Test-Path "D:\") { "D:\data" } else { "C:\data" }
$root = Read-Host "Where should data live? (press Enter for $defaultRoot)"
if ([string]::IsNullOrWhiteSpace($root)) {
    $root = $defaultRoot
}
Write-Host "  using: $root"

# --- 2. Databento API key (hidden prompt) -------------------------------

Write-Host ""
Write-Host "Paste your Databento Live API key. The cursor will NOT move and"
Write-Host "nothing will be displayed when you paste — that's intentional."
Write-Host "After pasting, press Enter."
Write-Host ""

$secureKey = Read-Host "Databento API key" -AsSecureString
$bstr = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($secureKey)
$plainKey = [System.Runtime.InteropServices.Marshal]::PtrToStringBSTR($bstr)
[System.Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr)

if (-not $plainKey -or $plainKey.Length -lt 10) {
    Write-Host ""
    Write-Host "ERROR: no key entered or too short." -ForegroundColor Red
    exit 1
}
if (-not $plainKey.StartsWith("db-")) {
    Write-Host ""
    Write-Host "ERROR: that doesn't look like a Databento key — should start with 'db-'." -ForegroundColor Red
    Write-Host "If you copied with extra whitespace, try again." -ForegroundColor Red
    exit 1
}

# --- 3. Set env vars persistently + for current session -----------------

[Environment]::SetEnvironmentVariable("BS_DATA_ROOT", $root, "User")
[Environment]::SetEnvironmentVariable("DATABENTO_API_KEY", $plainKey, "User")
$env:BS_DATA_ROOT = $root
$env:DATABENTO_API_KEY = $plainKey

# --- 4. Create directory tree -------------------------------------------

$dirs = @(
    (Join-Path $root "raw"),
    (Join-Path $root "raw\live"),
    (Join-Path $root "raw\historical"),
    (Join-Path $root "parquet"),
    (Join-Path $root "heartbeat"),
    (Join-Path $root "logs")
)
foreach ($d in $dirs) {
    New-Item -ItemType Directory -Path $d -Force | Out-Null
}

# --- 5. Sanity-test the Python side -------------------------------------

Write-Host ""
Write-Host "Testing Python + databento package..." -ForegroundColor Yellow
$pyTest = @'
import os, sys
try:
    import databento as db
    print(f"  databento {db.__version__}: OK")
except Exception as e:
    print(f"  databento import FAILED: {e}", file=sys.stderr)
    sys.exit(1)

key = os.environ.get("DATABENTO_API_KEY", "")
if not key.startswith("db-"):
    print("  DATABENTO_API_KEY env var not visible to Python", file=sys.stderr)
    sys.exit(1)
print(f"  env var DATABENTO_API_KEY: visible to Python ({key[:8]}...)")
print(f"  env var BS_DATA_ROOT:      {os.environ.get('BS_DATA_ROOT')}")

try:
    client = db.Live(key=key)
    print("  databento.Live client constructed: OK (auth tested when streaming starts)")
except Exception as e:
    print(f"  databento.Live() FAILED: {e}", file=sys.stderr)
    sys.exit(1)
'@

# Prefer the backend venv if it exists; otherwise fall back to system python
# and offer to install databento. README.md says backend uses py -3.12 -m venv .venv.
$venvPython = Join-Path $PSScriptRoot "..\backend\.venv\Scripts\python.exe"
if (Test-Path $venvPython) {
    $venvPython = (Resolve-Path $venvPython).Path
    $py = $venvPython
    Write-Host "  using backend venv: $py"
} else {
    $py = "python"
    Write-Host "  no backend\.venv found — using system 'python' on PATH"
    Write-Host "  (for the documented setup, run in another window:" -ForegroundColor DarkGray
    Write-Host "     cd ..\backend; py -3.12 -m venv .venv; .\.venv\Scripts\Activate.ps1; pip install -e .[dev]" -ForegroundColor DarkGray
    Write-Host "   then re-run this script.)" -ForegroundColor DarkGray
}

# If databento isn't importable, install it into whichever python we picked
& $py -c "import databento" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "  databento not importable in this python — installing now..." -ForegroundColor Yellow
    & $py -m pip install --quiet databento
    if ($LASTEXITCODE -ne 0) {
        Write-Host ""
        Write-Host "ERROR: 'pip install databento' failed. See output above." -ForegroundColor Red
        Write-Host "Hint: activate the backend venv first, or run 'pip install databento' manually." -ForegroundColor Red
        exit 1
    }
}

& $py -c $pyTest
if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "Setup test failed. Review the error above." -ForegroundColor Red
    exit 1
}

# --- 6. Done -------------------------------------------------------------

Write-Host ""
Write-Host "Setup complete." -ForegroundColor Green
Write-Host ""
Write-Host "Directories created under $root :"
foreach ($d in $dirs) {
    Write-Host "  $d"
}
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "  1. Open a NEW PowerShell window so env vars take effect."
Write-Host "  2. Run the ingester:"
Write-Host "       cd C:\Users\benbr\BacktestStation\backend"
if (Test-Path $venvPython) {
    Write-Host "       .\.venv\Scripts\Activate.ps1"
}
Write-Host "       python -m app.ingest.live"
Write-Host "  3. In another PowerShell window, tail the heartbeat live:"
Write-Host "       Get-Content $root\heartbeat\live_ingester.json -Wait"
Write-Host ""
