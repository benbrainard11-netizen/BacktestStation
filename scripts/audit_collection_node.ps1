# Read-only audit of a Windows machine to determine fitness as a
# BacktestStation data collection node. Run on ben-247 (or husky-247).
#
# Usage:
#   powershell -ExecutionPolicy Bypass -File audit_collection_node.ps1
#   OR double-click if execution policy allows
#
# Safe — no writes except the report file dropped on your Desktop.

$ErrorActionPreference = "Continue"
$out = [System.Collections.ArrayList]::new()

function Add-Line($line) {
    [void]$out.Add($line)
}
function Add-Section($title) {
    Add-Line ""
    Add-Line "===== $title ====="
}

Add-Line "BacktestStation collection-node audit"
Add-Line "Run at: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss zzz')"

Add-Section "SYSTEM"
$os = Get-CimInstance Win32_OperatingSystem
Add-Line "Hostname:    $env:COMPUTERNAME"
Add-Line "User:        $env:USERNAME"
Add-Line "OS:          $($os.Caption) $($os.Version)"
Add-Line "Uptime:      $([int]((Get-Date) - $os.LastBootUpTime).TotalHours) hours"

Add-Section "CPU"
$cpu = Get-CimInstance Win32_Processor | Select-Object -First 1
Add-Line "Model:       $($cpu.Name.Trim())"
Add-Line "Cores:       $($cpu.NumberOfCores) cores / $($cpu.NumberOfLogicalProcessors) threads"

Add-Section "RAM"
$totalGB = [math]::Round($os.TotalVisibleMemorySize / 1MB, 1)
$freeGB = [math]::Round($os.FreePhysicalMemory / 1MB, 1)
Add-Line "Total:       $totalGB GB"
Add-Line "Free:        $freeGB GB"

Add-Section "DISK"
Get-CimInstance Win32_LogicalDisk -Filter "DriveType=3" | ForEach-Object {
    if ($_.Size -gt 0) {
        $tGB = [math]::Round($_.Size / 1GB, 1)
        $fGB = [math]::Round($_.FreeSpace / 1GB, 1)
        $pct = [math]::Round(100 * $_.FreeSpace / $_.Size, 1)
        Add-Line "$($_.DeviceID)  $fGB GB free of $tGB GB ($pct% free)  $($_.VolumeName)"
    }
}

Add-Section "GPU (for future ML)"
try {
    Get-CimInstance Win32_VideoController | Where-Object { $_.Name -notmatch "Basic|Mirror" } | ForEach-Object {
        $vramGB = if ($_.AdapterRAM) { [math]::Round($_.AdapterRAM / 1GB, 1) } else { "unknown" }
        Add-Line "$($_.Name)  VRAM=$vramGB GB  driver=$($_.DriverVersion)"
    }
} catch { Add-Line "(could not enumerate GPUs)" }

Add-Section "PYTHON"
$pyCmd = Get-Command python -ErrorAction SilentlyContinue
if ($pyCmd) {
    Add-Line "python:      $(python --version 2>&1)"
    Add-Line "location:    $($pyCmd.Source)"
} else {
    Add-Line "python NOT in PATH"
}

Add-Section "KEY PYTHON PACKAGES"
$packages = @("databento", "fastapi", "sqlalchemy", "uvicorn", "pandas", "pyarrow")
foreach ($pkg in $packages) {
    $info = pip show $pkg 2>$null
    if ($LASTEXITCODE -eq 0 -and $info) {
        $version = ($info | Select-String -Pattern "^Version:").ToString().Replace("Version: ", "")
        Add-Line "$pkg`: $version"
    } else {
        Add-Line "$pkg`: NOT installed"
    }
}

Add-Section "TAILSCALE"
$tsCmd = Get-Command tailscale -ErrorAction SilentlyContinue
if ($tsCmd) {
    try {
        $tsJson = tailscale status --json 2>$null | ConvertFrom-Json
        if ($tsJson) {
            Add-Line "Self hostname: $($tsJson.Self.HostName)"
            Add-Line "Self DNS:      $($tsJson.Self.DNSName)"
            Add-Line "Self IPs:      $($tsJson.Self.TailscaleIPs -join ', ')"
            Add-Line "Online peers:"
            $tsJson.Peer.PSObject.Properties | ForEach-Object {
                $p = $_.Value
                $status = if ($p.Online) { "ONLINE " } else { "offline" }
                Add-Line "  $status  $($p.HostName.PadRight(25))  $($p.DNSName)"
            }
        }
    } catch { Add-Line "(tailscale found but status call failed)" }
} else {
    Add-Line "tailscale NOT in PATH"
}

Add-Section "LIKELY LIVE BOT / DATA DIRECTORIES"
$candidates = @(
    "C:\agent",
    "C:\BacktestStation",
    "D:\agent",
    "D:\data",
    "D:\BacktestStation",
    "$env:USERPROFILE\BacktestStation",
    "$env:USERPROFILE\Documents\RithmicTrader",
    "$env:USERPROFILE\AppData\Local\RithmicTrader",
    "$env:USERPROFILE\AppData\Roaming\Rithmic",
    "C:\Rithmic",
    "C:\RTraderPro"
)
foreach ($p in $candidates) {
    if (Test-Path $p) {
        try {
            $size = (Get-ChildItem $p -Recurse -File -ErrorAction SilentlyContinue -Depth 4 | Measure-Object -Property Length -Sum).Sum
            $sizeMB = if ($size) { [math]::Round($size / 1MB, 1) } else { 0 }
            Add-Line "EXISTS   $p  ($sizeMB MB)"
        } catch {
            Add-Line "EXISTS   $p  (could not size)"
        }
    }
}

Add-Section "DBN / DBZ FILES (scanning C:\ D:\ under common paths)"
$dataRoots = @("C:\agent", "C:\data", "C:\BacktestStation", "D:\data", "D:\BacktestStation", "$env:USERPROFILE\data")
$dbnFound = 0
foreach ($root in $dataRoots) {
    if (Test-Path $root) {
        Get-ChildItem -Path $root -Recurse -ErrorAction SilentlyContinue -Depth 6 `
            -Include "*.dbn", "*.dbz", "*.dbn.zst" |
            Select-Object -First 10 | ForEach-Object {
                Add-Line "$($_.FullName)  ($([math]::Round($_.Length / 1MB, 1)) MB, $($_.LastWriteTime.ToString('yyyy-MM-dd')))"
                $dbnFound++
            }
    }
}
if ($dbnFound -eq 0) { Add-Line "(no DBN files found in common paths)" }

Add-Section "RECENT CSV FILES UNDER USERPROFILE (top 10 by last-modified)"
try {
    Get-ChildItem -Path $env:USERPROFILE -Recurse -File -Filter "*.csv" -ErrorAction SilentlyContinue -Depth 5 |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 10 | ForEach-Object {
            Add-Line "$($_.FullName)  ($([math]::Round($_.Length / 1KB, 1)) KB, $($_.LastWriteTime.ToString('yyyy-MM-dd')))"
        }
} catch {}

Add-Section "PROCESSES (top 10 by memory, filtered)"
Get-Process -ErrorAction SilentlyContinue | Where-Object {
    $_.Name -match "python|node|rithmic|rtrader|tailscale|postgres|docker|uvicorn|next"
} | Sort-Object -Property WorkingSet64 -Descending | Select-Object -First 10 | ForEach-Object {
    $memMB = [math]::Round($_.WorkingSet64 / 1MB, 0)
    $path = if ($_.Path) { $_.Path } else { "(no path)" }
    Add-Line "$($_.Name.PadRight(20))  mem=${memMB}MB  $path"
}

Add-Section "LISTENING TCP PORTS (<50000)"
try {
    Get-NetTCPConnection -State Listen -ErrorAction SilentlyContinue |
        Where-Object { $_.LocalPort -lt 50000 -and $_.LocalPort -gt 1 } |
        Sort-Object LocalPort -Unique |
        Select-Object -First 20 | ForEach-Object {
            $procName = (Get-Process -Id $_.OwningProcess -ErrorAction SilentlyContinue).Name
            if (-not $procName) { $procName = "?" }
            Add-Line "$($_.LocalAddress):$($_.LocalPort.ToString().PadRight(6))  $procName"
        }
} catch { Add-Line "(Get-NetTCPConnection unavailable)" }

Add-Section "CURRENT LOAD (5 second sample)"
try {
    $cpu1 = (Get-Counter '\Processor(_Total)\% Processor Time' -SampleInterval 1 -MaxSamples 5 -ErrorAction SilentlyContinue).CounterSamples.CookedValue
    if ($cpu1) {
        $avgCpu = [math]::Round(($cpu1 | Measure-Object -Average).Average, 1)
        Add-Line "Avg CPU (5s): $avgCpu %"
    }
} catch { Add-Line "(could not sample CPU)" }
Add-Line "Free RAM:    $freeGB GB of $totalGB GB ($([math]::Round(100 * $freeGB / $totalGB, 1))% free)"

Add-Section "DONE"
Add-Line "Completed:   $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"

# Print to terminal
$out | ForEach-Object { Write-Host $_ }

# Save to desktop
$logPath = Join-Path $env:USERPROFILE "Desktop\bs_audit_$(Get-Date -Format 'yyyyMMdd_HHmmss').txt"
$out | Out-File -FilePath $logPath -Encoding utf8
Write-Host ""
Write-Host "Report saved to: $logPath"
Write-Host "Copy-paste the contents (or the file) back to Claude."
