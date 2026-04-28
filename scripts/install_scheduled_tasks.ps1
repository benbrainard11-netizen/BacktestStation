# Register the two recurring BacktestStation tasks on a Windows collection
# node:
#
#   1. BacktestStationParquetMirror -- hourly DBN -> parquet conversion so
#      /data and downstream queries stay current.
#   2. BacktestStationHistorical    -- monthly (day 1, 02:00 local) MBP-1
#      backfill so May 1 just works without manual setup.
#
# Both run as the current user with -LogonType S4U so they execute without
# requiring an interactive logon AND inherit User-scope env vars
# (BS_DATA_ROOT, DATABENTO_API_KEY) the same way other processes do.
#
# Run AFTER setup_ingester.ps1 has set the env vars. Needs admin (Task
# Scheduler registration is admin-only at the machine scope).
#
# Usage:
#   powershell -ExecutionPolicy Bypass -File scripts\install_scheduled_tasks.ps1
#
# Tear down:
#   Unregister-ScheduledTask -TaskName BacktestStationParquetMirror -Confirm:$false
#   Unregister-ScheduledTask -TaskName BacktestStationHistorical    -Confirm:$false

$ErrorActionPreference = "Stop"

$BackendDir = Resolve-Path (Join-Path $PSScriptRoot "..\backend")
$User       = "$env:USERDOMAIN\$env:USERNAME"

Write-Host ""
Write-Host "BacktestStation scheduled tasks installer" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# --- 1. Locate Python ----------------------------------------------------

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

# --- 2. Sanity-check env vars are set ------------------------------------

$dataRoot = [Environment]::GetEnvironmentVariable("BS_DATA_ROOT", "User")
if (-not $dataRoot) {
    Write-Host "ERROR: BS_DATA_ROOT not set at User scope. Run setup_ingester.ps1 first." -ForegroundColor Red
    exit 1
}
$apiKey = [Environment]::GetEnvironmentVariable("DATABENTO_API_KEY", "User")
if (-not $apiKey) {
    Write-Host "ERROR: DATABENTO_API_KEY not set at User scope. Run setup_ingester.ps1 first." -ForegroundColor Red
    exit 1
}
Write-Host "  BS_DATA_ROOT = $dataRoot"
Write-Host "  user         = $User"

# --- 3. Verify required Python packages ----------------------------------

Write-Host ""
Write-Host "Checking Python packages (databento, pyarrow)..." -ForegroundColor Yellow
& $pythonExe -c "import databento" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: 'databento' not importable from $pythonExe. Run 'pip install databento' in that interpreter." -ForegroundColor Red
    exit 1
}
& $pythonExe -c "import pyarrow" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: 'pyarrow' not importable from $pythonExe. Run 'pip install pyarrow' in that interpreter." -ForegroundColor Red
    exit 1
}
Write-Host "  databento + pyarrow OK"

# --- 4. Register parquet mirror (hourly) --------------------------------

Write-Host ""
Write-Host "Registering BacktestStationParquetMirror (hourly)..." -ForegroundColor Cyan

$pmAction = New-ScheduledTaskAction `
    -Execute $pythonExe `
    -Argument '-m app.ingest.parquet_mirror' `
    -WorkingDirectory $BackendDir

# Hourly trigger, indefinite duration. Omit -RepetitionDuration entirely:
# when it's not supplied, New-ScheduledTaskTrigger leaves the Duration
# field empty in the task XML, which Task Scheduler interprets as
# "repeat forever". Supplying any explicit large duration (e.g. 100y)
# gets rejected by the XSD validator (max ~P31D).
$pmTrigger = New-ScheduledTaskTrigger `
    -Once `
    -At (Get-Date).AddMinutes(2) `
    -RepetitionInterval (New-TimeSpan -Hours 1)

$pmSettings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -ExecutionTimeLimit (New-TimeSpan -Hours 4) `
    -MultipleInstances IgnoreNew

# 4h is generous on purpose. Normal hourly runs finish in seconds (just
# scan + skip-unchanged); the limit only matters when there's catchup
# to do after a backfill. Empirically (2026-04-27) a full warehouse
# catchup of ~30 per-symbol DBN files took ~45 min of wall time, and
# legacy multi-symbol files (~700 MB each) take 3-5 min apiece. The
# previous 30-min cap killed catchup runs mid-flight, so the next
# hourly fire would re-process the same files and get killed again.

# S4U: run as the current user without storing a password, in a
# non-interactive context. User env vars are still resolved.
$pmPrincipal = New-ScheduledTaskPrincipal `
    -UserId $User `
    -LogonType S4U `
    -RunLevel Limited

Register-ScheduledTask `
    -TaskName 'BacktestStationParquetMirror' `
    -Description 'Convert raw DBN files to per-symbol parquet, hourly' `
    -Action $pmAction `
    -Trigger $pmTrigger `
    -Settings $pmSettings `
    -Principal $pmPrincipal `
    -Force | Out-Null

# Verify it actually registered (Register-ScheduledTask sometimes emits
# non-terminating errors that ErrorActionPreference=Stop fails to halt on,
# so we can't trust the lack of a thrown exception).
if (-not (Get-ScheduledTask -TaskName 'BacktestStationParquetMirror' -ErrorAction SilentlyContinue)) {
    Write-Host "ERROR: BacktestStationParquetMirror did not register. See errors above." -ForegroundColor Red
    exit 1
}
Write-Host "  registered. First run in ~2 min, then every hour."

# --- 5. Register historical puller (monthly, day 1, 02:00) --------------

Write-Host ""
Write-Host "Registering BacktestStationHistorical (monthly, day 1 at 02:00)..." -ForegroundColor Cyan

# Monthly triggers via PowerShell's CIM cmdlets get tangled in PSTypeName
# mismatches that no amount of casting fixes (Register-ScheduledTask wants
# MSFT_TaskTrigger but New-CimInstance produces MSFT_TaskMonthlyTrigger and
# the type checker doesn't see the inheritance). Build the task as XML
# instead -- Register-ScheduledTask -Xml has its own parser and accepts
# the full Windows task schema, including ScheduleByMonth.
#
# StartBoundary uses today's date at 02:00 just so the schedule has a
# reference point; the actual fire dates come from DaysOfMonth + Months.

$startBoundary = (Get-Date '02:00:00').ToString('yyyy-MM-ddTHH:mm:ss')
$xmlEscapedBackend = $BackendDir.Path -replace '&', '&amp;' -replace '<', '&lt;' -replace '>', '&gt;'
$xmlEscapedPython  = $pythonExe       -replace '&', '&amp;' -replace '<', '&lt;' -replace '>', '&gt;'

$hXml = @"
<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.4" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo>
    <Description>Pull last full month of MBP-1 historical data on the 1st</Description>
  </RegistrationInfo>
  <Triggers>
    <CalendarTrigger>
      <StartBoundary>$startBoundary</StartBoundary>
      <Enabled>true</Enabled>
      <ScheduleByMonth>
        <DaysOfMonth><Day>1</Day></DaysOfMonth>
        <Months>
          <January /><February /><March /><April /><May /><June />
          <July /><August /><September /><October /><November /><December />
        </Months>
      </ScheduleByMonth>
    </CalendarTrigger>
  </Triggers>
  <Principals>
    <Principal id="Author">
      <UserId>$User</UserId>
      <LogonType>S4U</LogonType>
      <RunLevel>LeastPrivilege</RunLevel>
    </Principal>
  </Principals>
  <Settings>
    <ExecutionTimeLimit>PT2H</ExecutionTimeLimit>
    <Enabled>true</Enabled>
    <StartWhenAvailable>true</StartWhenAvailable>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <AllowStartOnDemand>true</AllowStartOnDemand>
  </Settings>
  <Actions Context="Author">
    <Exec>
      <Command>$xmlEscapedPython</Command>
      <Arguments>-m app.ingest.historical</Arguments>
      <WorkingDirectory>$xmlEscapedBackend</WorkingDirectory>
    </Exec>
  </Actions>
</Task>
"@

Register-ScheduledTask -TaskName 'BacktestStationHistorical' -Xml $hXml -Force | Out-Null

if (-not (Get-ScheduledTask -TaskName 'BacktestStationHistorical' -ErrorAction SilentlyContinue)) {
    Write-Host "ERROR: BacktestStationHistorical did not register. See errors above." -ForegroundColor Red
    exit 1
}
Write-Host "  registered. First run May 1 at 02:00 local."

# --- 5b. Register weekly gap-filler (Sunday 03:00 local) ----------------

Write-Host ""
Write-Host "Registering BacktestStationGapFiller (weekly, Sunday at 03:00)..." -ForegroundColor Cyan

# Weekly trigger via XML for the same reason as the monthly task
# (PowerShell CIM types don't compose cleanly). Sunday-3am gives the
# monthly historical fire (1st of the month, 02:00) plenty of time
# to settle, and lets the gap-filler catch any week the monthly run
# missed (e.g. Databento outage, holiday, scheduler hiccup).

$gfXml = @"
<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.4" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo>
    <Description>Weekly gap-filler: fill missing MBP-1 partitions in last 3 months, $0-cost only</Description>
  </RegistrationInfo>
  <Triggers>
    <CalendarTrigger>
      <StartBoundary>$startBoundary</StartBoundary>
      <Enabled>true</Enabled>
      <ScheduleByWeek>
        <DaysOfWeek><Sunday /></DaysOfWeek>
        <WeeksInterval>1</WeeksInterval>
      </ScheduleByWeek>
    </CalendarTrigger>
  </Triggers>
  <Principals>
    <Principal id="Author">
      <UserId>$User</UserId>
      <LogonType>S4U</LogonType>
      <RunLevel>LeastPrivilege</RunLevel>
    </Principal>
  </Principals>
  <Settings>
    <ExecutionTimeLimit>PT4H</ExecutionTimeLimit>
    <Enabled>true</Enabled>
    <StartWhenAvailable>true</StartWhenAvailable>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <AllowStartOnDemand>true</AllowStartOnDemand>
  </Settings>
  <Actions Context="Author">
    <Exec>
      <Command>$xmlEscapedPython</Command>
      <Arguments>-m app.ingest.gap_filler</Arguments>
      <WorkingDirectory>$xmlEscapedBackend</WorkingDirectory>
    </Exec>
  </Actions>
</Task>
"@

# Re-anchor StartBoundary to the next Sunday at 03:00 so the schedule
# fires consistently regardless of when the install ran.
$today = Get-Date
$daysUntilSunday = (7 - [int]$today.DayOfWeek) % 7
if ($daysUntilSunday -eq 0) { $daysUntilSunday = 7 }
$nextSunday = $today.Date.AddDays($daysUntilSunday).AddHours(3)
$gfStart = $nextSunday.ToString('yyyy-MM-ddTHH:mm:ss')
$gfXml = $gfXml -replace [regex]::Escape($startBoundary), $gfStart

Register-ScheduledTask -TaskName 'BacktestStationGapFiller' -Xml $gfXml -Force | Out-Null

if (-not (Get-ScheduledTask -TaskName 'BacktestStationGapFiller' -ErrorAction SilentlyContinue)) {
    Write-Host "ERROR: BacktestStationGapFiller did not register. See errors above." -ForegroundColor Red
    exit 1
}
Write-Host "  registered. First run $gfStart local (next Sunday 03:00)."

# --- 6. Summary ---------------------------------------------------------

Write-Host ""
Write-Host "Done." -ForegroundColor Green
Write-Host ""
Get-ScheduledTask | Where-Object { $_.TaskName -like 'BacktestStation*' } | `
    Select-Object TaskName, State, `
        @{n='Trigger';e={$_.Triggers[0].CimClass.CimClassName}}, `
        @{n='NextRun';e={(Get-ScheduledTaskInfo $_).NextRunTime}} | `
    Format-Table -AutoSize | Out-String -Width 200

Write-Host "Manage:"
Write-Host "  Get-ScheduledTask -TaskName BacktestStation*   # status"
Write-Host "  Start-ScheduledTask BacktestStationParquetMirror  # run-now"
Write-Host "  Unregister-ScheduledTask <name> -Confirm:`$false  # remove"
Write-Host ""
