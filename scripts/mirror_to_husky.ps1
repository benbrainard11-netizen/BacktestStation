# Mirror the BacktestStation data warehouse from this 24/7 collection node
# (ben-247) to Husky's 24/7 PC over Tailscale. Cold backup of the live
# ingester output + parquet mirror + historical pulls.
#
# This is a STUB: the network path + scheduling are placeholders pending
# Husky's Tailscale hostname and a chosen dest path. Wire those up below
# (see TODOs) before adding to install_scheduled_tasks.ps1.
#
# Design: use robocopy (Windows-native, no extra install) with /E /XO /Z
# semantics so the mirror is incremental, resumable, and never destroys
# files on the dest that aren't present on the source. NOT /MIR -- that
# would delete dest files when source rotates them away, which is the
# opposite of "cold backup".
#
# Usage:
#   powershell -ExecutionPolicy Bypass -File scripts\mirror_to_husky.ps1
#
# Override defaults via env vars:
#   BS_DATA_ROOT          source (default: D:\data)
#   BS_HUSKY_MIRROR_DEST  dest UNC path (no default -- script errors out
#                         if unset; safer than guessing a path)

$ErrorActionPreference = "Stop"

# --- 1. Resolve source + dest -------------------------------------------

$src = [Environment]::GetEnvironmentVariable("BS_DATA_ROOT", "User")
if (-not $src) { $src = "D:\data" }

$dest = [Environment]::GetEnvironmentVariable("BS_HUSKY_MIRROR_DEST", "User")
if (-not $dest) {
    Write-Host "ERROR: BS_HUSKY_MIRROR_DEST not set." -ForegroundColor Red
    Write-Host "  Set it to a Tailscale UNC path or mapped drive on Husky's PC, e.g.:" -ForegroundColor Yellow
    Write-Host '    [Environment]::SetEnvironmentVariable("BS_HUSKY_MIRROR_DEST", "\\husky-247\backteststation-data", "User")' -ForegroundColor Yellow
    Write-Host "  TODO: confirm Husky's Tailscale hostname + share path before wiring this up." -ForegroundColor Yellow
    exit 1
}

if (-not (Test-Path $src)) {
    Write-Host "ERROR: source path missing: $src" -ForegroundColor Red
    exit 1
}

# --- 2. Log file --------------------------------------------------------

$logDir = Join-Path $src "logs"
if (-not (Test-Path $logDir)) { New-Item -ItemType Directory -Path $logDir -Force | Out-Null }
$logFile = Join-Path $logDir "husky_mirror.log"

Write-Host ""
Write-Host "Mirror to Husky (cold backup)" -ForegroundColor Cyan
Write-Host "==============================" -ForegroundColor Cyan
Write-Host "  src:  $src"
Write-Host "  dest: $dest"
Write-Host "  log:  $logFile"
Write-Host ""

# --- 3. Robocopy --------------------------------------------------------

# /E    copy subdirectories incl. empty
# /XO   skip files where dest is newer (idempotent re-runs are cheap)
# /Z    resumable -- helpful over Tailscale if the link blips
# /R:3  retry 3x on per-file failure
# /W:5  5s between retries
# /MT:8 8 threads (Tailscale + HDD-on-dest -- don't crank this)
# /NDL  no per-directory log spam
# /NP   no per-file progress (keep log small)
# /TEE  print to console AND append to log
# /LOG+ append (don't overwrite the log between runs)

$robocopyArgs = @(
    $src, $dest,
    "/E", "/XO", "/Z",
    "/R:3", "/W:5",
    "/MT:8",
    "/NDL", "/NP",
    "/TEE",
    "/LOG+:$logFile"
)

robocopy @robocopyArgs

# Robocopy uses non-zero exit codes to mean "files were copied" -- not
# errors. Codes 0-7 are success-ish, 8+ are real failures.
# https://learn.microsoft.com/en-us/troubleshoot/windows-server/backup-and-storage/return-code-robocopy
$rc = $LASTEXITCODE
if ($rc -ge 8) {
    Write-Host ""
    Write-Host "ERROR: robocopy exited $rc (>= 8 = real failure). See $logFile" -ForegroundColor Red
    exit $rc
}

Write-Host ""
Write-Host "Done. robocopy exit=$rc (0-7 OK; lower bits == files-copied flags)." -ForegroundColor Green
exit 0
