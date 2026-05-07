# Install the BacktestStation daily Databento pull as a Windows Scheduled Task.
#
# Runs daily at 5:30 PM ET (mid-CME daily break, when futures are closed).
# CME closes 5:00 PM ET and reopens 6:00 PM ET on weekdays. Pulling at 5:30
# means yesterday's data is fully settled and Databento has it ready.
#
# This script must be run from an ELEVATED (Admin) PowerShell prompt.
# Re-run anytime to update the task definition.

$ErrorActionPreference = "Stop"

$TaskName = "BacktestStationDailyPull"
$PythonExe = "C:\Users\benbr\AppData\Local\Programs\Python\Python312\pythonw.exe"
$WorkingDir = "C:\Users\benbr\BacktestStation\backend"
$ModuleArg = "-m app.ingest.daily"

# 5:30 PM Eastern. Phoenix (no DST) sits on MST = UTC-7 year-round.
# ET = UTC-5 (DST) or UTC-4 (EST). The simplest portable choice: pin
# the trigger to a fixed Phoenix wall-clock time that maps to 5:30 PM
# ET during EDT (March-Nov, the bulk of the year). Reassess once a year.
#
# 5:30 PM ET (EDT) = 2:30 PM Phoenix
# 5:30 PM ET (EST) = 3:30 PM Phoenix
# Trigger: 2:30 PM local. During EST months it'll fire at 4:30 PM ET,
# still inside the CME break. Acceptable for now; refine if it matters.
$TriggerTime = "14:30"

Write-Host "Installing scheduled task '$TaskName'..."

# Wipe any prior version so re-runs are idempotent
$existing = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($existing) {
    Write-Host "  removing existing task definition"
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
}

$action = New-ScheduledTaskAction `
    -Execute $PythonExe `
    -Argument $ModuleArg `
    -WorkingDirectory $WorkingDir

$trigger = New-ScheduledTaskTrigger -Daily -At $TriggerTime

# StartWhenAvailable: run on next login if PC was off at trigger time.
# RunOnlyIfNetworkAvailable: skip if no internet (no point pulling).
# AllowStartIfOnBatteries + DontStopIfGoingOnBatteries: 24/7 home PC, always plugged in.
$settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -RunOnlyIfNetworkAvailable `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -ExecutionTimeLimit (New-TimeSpan -Hours 2)

# Run as the current user (Ben), with stored creds so it fires even when
# nobody is logged in. LeastPrivilege so Claude Code can manage it later
# without admin elevation (matches the FractalAMD_Bot setup).
$principal = New-ScheduledTaskPrincipal `
    -UserId "$env:USERDOMAIN\$env:USERNAME" `
    -LogonType S4U `
    -RunLevel Limited

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Principal $principal `
    -Description "Pull yesterday's MBP-1 (NQ/ES/YM) + TBBO (CL/NG/GC/SI/ZN/ZB/ZF/6E/6B/6J) from Databento. Cost-checked, aborts if quote > `$0.01."

Write-Host ""
Write-Host "Installed. Verify with:"
Write-Host "  Get-ScheduledTask -TaskName '$TaskName'"
Write-Host ""
Write-Host "Run on demand (will pull yesterday UTC):"
Write-Host "  Start-ScheduledTask -TaskName '$TaskName'"
Write-Host ""
Write-Host "Logs: C:\data\logs\daily.log"
