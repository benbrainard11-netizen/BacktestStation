# Read-only status snapshot for Hermes.
#
# Prints a compact view of:
#   - timestamp + repo location
#   - current git branch, latest commit, dirty files
#   - selected backend endpoints if uvicorn is running on localhost:8000
#   - tail of recent relevant logs
#
# Hard rules: this script never writes files, never starts servers, never
# pulls paid data, never deletes anything. If something is missing or
# offline, it prints a friendly note and keeps going.
#
# Usage:
#   powershell -ExecutionPolicy Bypass -File scripts\hermes_status_snapshot.ps1
#   .\scripts\hermes_status_snapshot.ps1
#   .\scripts\hermes_status_snapshot.ps1 | Out-File -Encoding utf8 snapshot.txt

$ErrorActionPreference = "Continue"

# Resolve repo root from the script's own location ($PSScriptRoot is the
# directory holding this file). Falls back to current working directory if
# the script is invoked in an unusual way.
$repoRoot = Split-Path -Parent $PSScriptRoot
if (-not $repoRoot -or -not (Test-Path (Join-Path $repoRoot ".git"))) {
    $repoRoot = (Get-Location).Path
}

function Write-Section([string]$title) {
    Write-Output ""
    Write-Output "===== $title ====="
}

function Test-LocalPort([int]$port, [int]$timeoutMs = 500) {
    $client = $null
    try {
        $client = New-Object System.Net.Sockets.TcpClient
        $iar = $client.BeginConnect("127.0.0.1", $port, $null, $null)
        $ok = $iar.AsyncWaitHandle.WaitOne($timeoutMs, $false)
        if ($ok -and $client.Connected) { return $true }
        return $false
    } catch {
        return $false
    } finally {
        if ($client) { $client.Close() }
    }
}

Write-Output "Hermes status snapshot"
Write-Output "Generated: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss zzz')"
Write-Output "Repo:      $repoRoot"

# ---------------------------------------------------------------------------
# GIT
# ---------------------------------------------------------------------------
Write-Section "GIT"

$branch = git -C $repoRoot branch --show-current
if ($LASTEXITCODE -eq 0 -and $branch) {
    Write-Output "Branch:    $branch"
} else {
    Write-Output "Branch:    (unavailable - not a git repo or git missing)"
}

$lastCommit = git -C $repoRoot log -1 --pretty=format:"%h %ad %s" --date=short
if ($LASTEXITCODE -eq 0 -and $lastCommit) {
    Write-Output "Latest:    $lastCommit"
}

Write-Output ""
Write-Output "git status --short:"
$gitStatus = @(git -C $repoRoot status --short)
if ($LASTEXITCODE -eq 0) {
    if ($gitStatus.Count -eq 0) {
        Write-Output "  (clean)"
    } else {
        foreach ($line in $gitStatus) { Write-Output "  $line" }
    }
} else {
    Write-Output "  (git status failed)"
}

# ---------------------------------------------------------------------------
# BACKEND
# ---------------------------------------------------------------------------
Write-Section "BACKEND"

$baseUrl = "http://localhost:8000"
# Note: Ben's spec listed "/api/monitor" but the real mounted endpoint is
# "/api/monitor/live" (the bare path 404s). We probe the canonical endpoint.
$endpoints = @(
    @{ Name = "health";            Path = "/api/health" },
    @{ Name = "data-health";       Path = "/api/data-health" },
    @{ Name = "monitor live";      Path = "/api/monitor/live" },
    @{ Name = "knowledge health";  Path = "/api/knowledge/health" },
    @{ Name = "datasets coverage"; Path = "/api/datasets/coverage" }
)

if (-not (Test-LocalPort 8000)) {
    Write-Output "BACKEND OFFLINE: nothing listening on http://localhost:8000"
    Write-Output "(to start it: cd backend; uvicorn app.main:app --reload --port 8000)"
} else {
    foreach ($ep in $endpoints) {
        $url = $baseUrl + $ep.Path
        try {
            $resp = Invoke-RestMethod -Uri $url -Method Get -TimeoutSec 8 -ErrorAction Stop
            $json = $resp | ConvertTo-Json -Depth 4 -Compress
            if ($json -and $json.Length -gt 800) {
                $json = $json.Substring(0, 800) + "...(truncated)"
            }
            Write-Output ("[{0,-18}] OK   {1}" -f $ep.Name, $ep.Path)
            if ($json) { Write-Output "    $json" }
        } catch {
            $msg = $_.Exception.Message
            $code = $null
            if ($_.Exception.Response) {
                $code = [int]$_.Exception.Response.StatusCode
            }
            if ($code) {
                Write-Output ("[{0,-18}] HTTP {1} {2}" -f $ep.Name, $code, $ep.Path)
            } else {
                Write-Output ("[{0,-18}] ERR  {1} -- {2}" -f $ep.Name, $ep.Path, $msg)
            }
        }
    }
}

# ---------------------------------------------------------------------------
# LOGS
# ---------------------------------------------------------------------------
Write-Section "LOGS"

$logCandidates = @(
    "data\live_inbox\import.log"
)

$foundAnyLog = $false
foreach ($rel in $logCandidates) {
    $path = Join-Path $repoRoot $rel
    if (Test-Path $path) {
        $foundAnyLog = $true
        $info = Get-Item $path
        $sizeKb = [math]::Round($info.Length / 1KB, 1)
        Write-Output "$rel  ($sizeKb KB, modified $($info.LastWriteTime))"
        Write-Output "  --- last 20 lines ---"
        try {
            Get-Content -Path $path -Tail 20 -ErrorAction Stop | ForEach-Object {
                Write-Output "  $_"
            }
        } catch {
            Write-Output "  (could not read tail: $($_.Exception.Message))"
        }
        Write-Output ""
    }
}
if (-not $foundAnyLog) {
    Write-Output "(no candidate log files found)"
}

Write-Output ""
Write-Output "===== END SNAPSHOT ====="
