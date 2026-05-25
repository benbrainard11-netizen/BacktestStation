# Run the BacktestStation MBO-to-R2 mirror once.
#
# This script is intentionally small so Windows Task Scheduler can call it
# without needing complex quoting in the task action.

$ErrorActionPreference = "Stop"

$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$BackendDir = Join-Path $RepoRoot "backend"
$VenvPython = Join-Path $BackendDir ".venv\Scripts\python.exe"

if (Test-Path $VenvPython) {
    $PythonExe = (Resolve-Path $VenvPython).Path
} else {
    $cmd = Get-Command python -ErrorAction Stop
    $PythonExe = $cmd.Source
}

Set-Location $BackendDir
& $PythonExe -m app.ingest.mbo_r2_mirror
exit $LASTEXITCODE

