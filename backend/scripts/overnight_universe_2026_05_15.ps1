#requires -Version 5
# Overnight universe expansion runner — chains the cluster sweeps,
# dep-cleanup equal_levels passes, cross-symbol detectors, manifest
# checkpoints, and writes a final status doc.
#
# Designed to be idempotent: skip-on-error inside each scan + each cluster
# is its own log file.

$ErrorActionPreference = "Continue"
$VerbosePreference     = "Continue"
$py      = "C:\Users\benbr\AppData\Local\Python\bin\python.exe"
$repo    = "C:\Users\benbr\BacktestStation"
$backend = "$repo\backend"
$logRoot = "$repo\logs\overnight_universe_2026_05_15"
New-Item -ItemType Directory -Path $logRoot -Force | Out-Null
$mainLog = "$logRoot\main.log"

function Write-Step($msg) {
    $ts = (Get-Date -Format "yyyy-MM-dd HH:mm:ss")
    $line = "[$ts] $msg"
    Add-Content -Path $mainLog -Value $line
    Write-Output $line
}

function Run-Expand {
    param(
        [string[]]$Symbols,
        [string]$Start,
        [string]$End,
        [string[]]$Exclude = @(),
        [string[]]$Include = @(),
        [string]$Tag
    )
    Write-Step "START $Tag : symbols=$($Symbols -join ',') start=$Start end=$End"
    $argList = @("-m","scripts.expand_universe_run","--symbols") + $Symbols + @("--start",$Start,"--end",$End)
    if ($Exclude.Count -gt 0) { $argList += @("--exclude-detectors") + $Exclude }
    if ($Include.Count -gt 0) { $argList += @("--include-detectors") + $Include }
    Push-Location $backend
    $sw = [System.Diagnostics.Stopwatch]::StartNew()
    try {
        & $py @argList *>> $mainLog
    } catch {
        Write-Step "EXCEPTION in $Tag : $_"
    }
    $sw.Stop()
    Pop-Location
    $mins = [math]::Round($sw.Elapsed.TotalMinutes, 1)
    Write-Step "FINISH $Tag : ${mins} min"
}

function Run-Manifest {
    param([string]$Tag)
    Write-Step "START manifest $Tag"
    Push-Location $backend
    try {
        & $py -m scripts.ml.build_asset_universe_manifest *>> $mainLog
    } catch {
        Write-Step "EXCEPTION in manifest ${Tag} : $_"
    }
    Pop-Location
    Copy-Item "$repo\data\ml\catalog\asset_universe_manifest.json" "$logRoot\manifest_${Tag}.json" -Force -ErrorAction SilentlyContinue
    Write-Step "FINISH manifest $Tag"
}

$excludeDeps = @("equal_levels","psp_candle_divergence","smt_htf_reference_divergence")

Write-Step "=== Overnight universe expansion start ==="

# Step 2 (1 already done outside this script: the ES/NQ/YM backfill).
# Re-run equal_levels for all 4 indices (post-swing_pivot now exists).
Run-Expand `
    -Symbols @("ES.c.0","NQ.c.0","YM.c.0","RTY.c.0") `
    -Start "2015-01-01" -End "2026-05-05" `
    -Include @("equal_levels") `
    -Tag "indices_equal_levels"

# Step 3: cross-symbol PSP + SMT on the 4 indices.
Run-Expand `
    -Symbols @("ES.c.0","NQ.c.0","YM.c.0","RTY.c.0") `
    -Start "2015-01-01" -End "2026-05-05" `
    -Include @("psp_candle_divergence","smt_htf_reference_divergence") `
    -Tag "indices_cross_symbol"

# Step 4: manifest checkpoint — 4-index baseline.
Run-Manifest -Tag "after_indices"

# Step 5: rates cluster.
Run-Expand `
    -Symbols @("ZB.c.0","ZN.c.0","ZF.c.0","ZT.c.0") `
    -Start "2018-05-01" -End "2026-04-25" `
    -Exclude $excludeDeps `
    -Tag "rates"

# Step 6: energies cluster.
Run-Expand `
    -Symbols @("CL.c.0","BZ.c.0","HO.c.0","RB.c.0","NG.c.0") `
    -Start "2018-05-01" -End "2026-04-25" `
    -Exclude $excludeDeps `
    -Tag "energies"

# Step 7: metals cluster.
Run-Expand `
    -Symbols @("GC.c.0","SI.c.0","PA.c.0","PL.c.0","HG.c.0") `
    -Start "2018-05-01" -End "2026-04-25" `
    -Exclude $excludeDeps `
    -Tag "metals"

# Step 8: grains cluster.
Run-Expand `
    -Symbols @("ZC.c.0","ZS.c.0","ZW.c.0") `
    -Start "2018-05-01" -End "2026-04-25" `
    -Exclude $excludeDeps `
    -Tag "grains"

# Step 9: FX majors cluster.
Run-Expand `
    -Symbols @("6A.c.0","6B.c.0","6C.c.0","6E.c.0","6J.c.0","6N.c.0","6S.c.0") `
    -Start "2018-05-01" -End "2026-04-25" `
    -Exclude $excludeDeps `
    -Tag "fx"

# Step 10: bulk equal_levels for all newly-added symbols.
Run-Expand `
    -Symbols @("ZB.c.0","ZN.c.0","ZF.c.0","ZT.c.0", `
               "CL.c.0","BZ.c.0","HO.c.0","RB.c.0","NG.c.0", `
               "GC.c.0","SI.c.0","PA.c.0","PL.c.0","HG.c.0", `
               "ZC.c.0","ZS.c.0","ZW.c.0", `
               "6A.c.0","6B.c.0","6C.c.0","6E.c.0","6J.c.0","6N.c.0","6S.c.0") `
    -Start "2018-05-01" -End "2026-04-25" `
    -Include @("equal_levels") `
    -Tag "all_new_equal_levels"

# Step 11: cross-symbol detectors on the full 26-symbol universe.
Run-Expand `
    -Symbols @("ES.c.0","NQ.c.0","YM.c.0","RTY.c.0", `
               "ZB.c.0","ZN.c.0","ZF.c.0","ZT.c.0", `
               "CL.c.0","BZ.c.0","HO.c.0","RB.c.0","NG.c.0", `
               "GC.c.0","SI.c.0","PA.c.0","PL.c.0","HG.c.0", `
               "ZC.c.0","ZS.c.0","ZW.c.0", `
               "6A.c.0","6B.c.0","6C.c.0","6E.c.0","6J.c.0","6N.c.0","6S.c.0") `
    -Start "2018-05-01" -End "2026-05-05" `
    -Include @("psp_candle_divergence","smt_htf_reference_divergence") `
    -Tag "all_cross_symbol"

# Step 12: final manifest.
Run-Manifest -Tag "final"

Write-Step "=== Overnight universe expansion complete ==="
Write-Step "Logs: $logRoot"
