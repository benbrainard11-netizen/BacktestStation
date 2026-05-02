# Clean-launch the Tauri desktop app for development.
#
# Kills any leftover insyncalgo-desktop / node / sidecar python that may be
# holding ports 3000 + 8000 from a previous session, nukes the .next cache so
# stale build manifests don't 500 the routes, then starts `tauri dev` fresh.
#
# Usage:  pwsh frontend/scripts/dev.ps1
#         (or `npm run dev:clean` if you wire it into package.json)

$ErrorActionPreference = "SilentlyContinue"

Write-Host "[dev] Killing leftover dev processes..." -ForegroundColor DarkGray
Get-Process -Name insyncalgo-desktop, insyncalgo_lib, node, python, cargo |
    Stop-Process -Force
Start-Sleep -Seconds 2

# Wipe stale Next.js dev cache — repeat restarts corrupt this and produce
# "missing bootstrap script" / ENOENT app-paths-manifest.json errors.
$root = Split-Path -Parent $PSScriptRoot
$next = Join-Path $root ".next"
if (Test-Path $next) {
    Write-Host "[dev] Wiping .next cache..." -ForegroundColor DarkGray
    Remove-Item -Recurse -Force $next
}

Write-Host "[dev] Launching tauri dev..." -ForegroundColor Cyan
Push-Location $root
try {
    npm run tauri:dev
} finally {
    Pop-Location
}
