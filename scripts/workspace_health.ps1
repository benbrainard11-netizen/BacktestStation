param(
    [string]$Root = "C:\Users\benbr"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Continue"

function Write-Section {
    param([string]$Title)
    Write-Host ""
    Write-Host "== $Title =="
}

function Write-GitSummary {
    param(
        [string]$Name,
        [string]$Path
    )

    Write-Host ""
    Write-Host "[$Name] $Path"
    if (-not (Test-Path $Path)) {
        Write-Host "missing"
        return
    }

    $inside = & git -C $Path rev-parse --is-inside-work-tree 2>$null
    if ($LASTEXITCODE -ne 0 -or $inside -ne "true") {
        Write-Host "not a git worktree"
        return
    }

    & git -C $Path status --short --branch
}

function Write-EnvPresence {
    param([string]$Name)

    $processValue = [Environment]::GetEnvironmentVariable($Name, "Process")
    $userValue = [Environment]::GetEnvironmentVariable($Name, "User")
    $machineValue = [Environment]::GetEnvironmentVariable($Name, "Machine")

    $scopes = @()
    if ($processValue) { $scopes += "process" }
    if ($userValue) { $scopes += "user" }
    if ($machineValue) { $scopes += "machine" }

    if ($scopes.Count -eq 0) {
        Write-Host "${Name}: missing"
    } else {
        Write-Host "${Name}: set ($($scopes -join ', '))"
    }
}

function Write-ScheduledTaskSummary {
    param([string]$TaskName)

    try {
        $task = Get-ScheduledTask -TaskName $TaskName -ErrorAction Stop
        $info = Get-ScheduledTaskInfo -TaskName $TaskName -ErrorAction SilentlyContinue
        $nextRun = if ($info) { $info.NextRunTime } else { "" }
        $lastResult = if ($info) { $info.LastTaskResult } else { "" }
        Write-Host "${TaskName}: state=$($task.State) next=$nextRun last_result=$lastResult"
        return
    } catch {
        $queryError = $_.Exception.Message
    }

    $systemRoot = $env:SystemRoot
    if (-not $systemRoot) {
        $systemRoot = "C:\Windows"
    }
    $taskFile = Join-Path $systemRoot ("System32\Tasks\" + $TaskName.TrimStart("\"))
    if (-not (Test-Path -LiteralPath $taskFile)) {
        Write-Host "${TaskName}: not installed or query blocked ($queryError)"
        return
    }

    try {
        $raw = Get-Content -Raw -LiteralPath $taskFile -ErrorAction Stop
        $start = [regex]::Match($raw, "<StartBoundary>([^<]+)</StartBoundary>").Groups[1].Value
        $enabled = [regex]::Match($raw, "<Enabled>([^<]+)</Enabled>").Groups[1].Value
        $command = [regex]::Match($raw, "<Command>([^<]+)</Command>").Groups[1].Value
        Write-Host "${TaskName}: installed (task file present; Scheduler query blocked: $queryError) start=$start enabled=$enabled command=$command"
    } catch {
        Write-Host "${TaskName}: installed (task file present; details blocked: $($_.Exception.Message))"
    }
}

Write-Host "BacktestStation workspace health"
Write-Host "Root: $Root"
Write-Host "Timestamp: $((Get-Date).ToString('yyyy-MM-dd HH:mm:ss zzz'))"

Write-Section "Git"
Write-GitSummary "BacktestStation" (Join-Path $Root "BacktestStation")
Write-GitSummary "InsyncAPP" (Join-Path $Root "InsyncAPP")
Write-GitSummary "InsyncAPP_247" (Join-Path $Root "InsyncAPP_247")
Write-GitSummary "InsyncAPP_ben_merge" (Join-Path $Root "InsyncAPP_ben_merge")
Write-GitSummary "InsyncAPP_market_relay" (Join-Path $Root "InsyncAPP_market_relay")
Write-GitSummary "InsyncAPP_shared_chart" (Join-Path $Root "InsyncAPP_shared_chart")

Write-Section "InsyncApp Worktrees"
$insync = Join-Path $Root "InsyncAPP"
if (Test-Path $insync) {
    & git -C $insync worktree list
} else {
    Write-Host "InsyncAPP missing; cannot list worktrees"
}

Write-Section "Environment"
Write-EnvPresence "BS_DATA_ROOT"
Write-EnvPresence "BS_DATA_BACKEND"
Write-EnvPresence "BS_R2_BUCKET"
Write-EnvPresence "BS_R2_ENDPOINT"
Write-EnvPresence "BS_R2_ACCESS_KEY"
Write-EnvPresence "BS_R2_SECRET"
Write-EnvPresence "DATABENTO_API_KEY"

$dataRoot = [Environment]::GetEnvironmentVariable("BS_DATA_ROOT", "Process")
if (-not $dataRoot) {
    $dataRoot = [Environment]::GetEnvironmentVariable("BS_DATA_ROOT", "User")
}
if (-not $dataRoot) {
    $dataRoot = [Environment]::GetEnvironmentVariable("BS_DATA_ROOT", "Machine")
}

Write-Section "External Warehouse"
if ($dataRoot) {
    Write-Host "BS_DATA_ROOT: $dataRoot"
    $checks = @(
        "raw\databento\tbbo",
        "raw\databento\mbp-1",
        "raw\databento\mbo",
        "processed\bars\timeframe=1m"
    )
    foreach ($rel in $checks) {
        $path = Join-Path $dataRoot $rel
        if (Test-Path $path) {
            Write-Host "${rel}: present"
        } else {
            Write-Host "${rel}: missing"
        }
    }
} else {
    Write-Host "BS_DATA_ROOT is not set"
}

Write-Section "Repo-Local Data"
$bsRepo = Join-Path $Root "BacktestStation"
$repoDataChecks = @(
    "data\research_events",
    "data\ml",
    "data\meta.sqlite",
    "logs"
)
foreach ($rel in $repoDataChecks) {
    $path = Join-Path $bsRepo $rel
    if (Test-Path $path) {
        Write-Host "${rel}: present"
    } else {
        Write-Host "${rel}: missing"
    }
}

Write-Section "Relevant Processes"
Get-Process |
    Where-Object {
        $_.ProcessName -match "insync|python|node|pnpm|uvicorn"
    } |
    Select-Object Id, ProcessName, Path |
    Format-Table -AutoSize

Write-Section "Scheduled Tasks"
$taskNames = @(
    "BacktestStationMboR2Mirror",
    "BacktestStationR2Upload",
    "BacktestStationParquetMirror",
    "BacktestStationDailyPull"
)
foreach ($taskName in $taskNames) {
    Write-ScheduledTaskSummary $taskName
}
