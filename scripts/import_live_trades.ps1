# Daily live-trades import.
# 1. Drain Taildrop inbox into live_inbox/.
# 2. If trades.jsonl is present, run the live JSONL importer against meta.sqlite.
# Scheduled by: schtasks /TN "BacktestStation - Import Live Trades"

$ErrorActionPreference = "Continue"
$inbox       = "C:\Users\benbr\BacktestStation\data\live_inbox"
$backend_dir = "C:\Users\benbr\BacktestStation\backend"
$venv_python = Join-Path $backend_dir ".venv\Scripts\python.exe"
$jsonl       = Join-Path $inbox "trades.jsonl"
$log         = Join-Path $inbox "import.log"

if (-not (Test-Path $inbox)) { New-Item -ItemType Directory -Path $inbox -Force | Out-Null }

function Log($msg) {
    $ts = Get-Date -Format "yyyy-MM-ddTHH:mm:sszzz"
    "$ts $msg" | Out-File -FilePath $log -Append -Encoding utf8
}

Log "=== run start ==="

# Drain whatever's in the Taildrop inbox.
$taildropOut = & tailscale file get --conflict=overwrite $inbox 2>&1
foreach ($line in $taildropOut) { Log ("taildrop: " + $line) }

if (-not (Test-Path $jsonl)) {
    Log "no trades.jsonl in inbox after taildrop drain - exiting clean"
    exit 0
}

$mtime = (Get-Item $jsonl).LastWriteTime
Log ("found trades.jsonl mtime=" + $mtime.ToString("o"))

Push-Location $backend_dir
try {
    $importerOut = & $venv_python -m app.ingest.live_trades_jsonl `
        --jsonl $jsonl `
        --time-zone "America/New_York" `
        --strategy-version-id 2 `
        --symbol "NQ.c.0" 2>&1
    $rc = $LASTEXITCODE
} finally {
    Pop-Location
}

foreach ($line in $importerOut) { Log ("importer: " + $line) }

if ($rc -ne 0) {
    Log ("importer FAILED rc=" + $rc)
    exit $rc
}

Log "=== run ok ==="
exit 0
