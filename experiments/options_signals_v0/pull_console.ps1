# VISIBLE options-data puller. Double-click PULL_OPTIONS_DATA.bat on the Desktop to run.
# Leave this window open. Status prints every minute; auto-revives the download if stalled.
# Safe to re-run any time (freshness-gated, never duplicates work). ASCII ONLY (PS 5.1 reads ANSI).
$ErrorActionPreference = 'SilentlyContinue'
$host.UI.RawUI.WindowTitle = "OPTIONS DATA PULLER - leave open"
$revive = 'C:\Users\benbr\BacktestStation\experiments\options_signals_v0\revive_pulls.ps1'
$shards = 'C:\Users\benbr\BacktestStation\experiments\options_signals_v0\out\_shards'
$pat = 'gex_' + 'shard'

Write-Host ""
Write-Host "=====================================================" -ForegroundColor Cyan
Write-Host "  OPTIONS ARCHIVE PULLER (SPX/RUT/DJX/NDX/GLD/SLV)" -ForegroundColor Cyan
Write-Host "  Leave this window open. Status prints every minute." -ForegroundColor Cyan
Write-Host "  Closing it does NOT stop downloads - re-open to" -ForegroundColor Cyan
Write-Host "  resume watching. GREEN = good, RED = auto-fixing." -ForegroundColor Cyan
Write-Host "=====================================================" -ForegroundColor Cyan
Write-Host ""

while ($true) {
    & $revive
    $c = Get-ChildItem D:\data\raw\thetadata -Recurse -File
    $newest = ($c | Sort-Object LastWriteTime -Descending | Select-Object -First 1).LastWriteTime
    $ageMin = [Math]::Round(((Get-Date) - $newest).TotalMinutes, 1)
    $n = (Get-CimInstance Win32_Process -Filter "Name='python.exe'" | Where-Object { $_.CommandLine -like "*$pat*" } | Measure-Object).Count
    $spxDone = (Get-ChildItem $shards -Filter 'spx_s*.parquet' | Where-Object { $_.Name -notlike '*spot*' } | Measure-Object).Count
    $gb = [Math]::Round((($c | Measure-Object Length -Sum).Sum / 1GB), 2)
    # Terminal serves slowly (~40s/req) and a single expiration can take 1-2 min, so "fresh"
    # is generous: green <= 12 min, yellow <= 30, red beyond (reviver only acts at 30+).
    $color = if ($ageMin -le 12) { 'Green' } elseif ($ageMin -le 30) { 'Yellow' } else { 'Red' }
    Write-Host ("{0}  files={1}  size={2}GB  last-download={3}min-ago  pullers={4}  SPX-parts-done={5}/3" -f
        (Get-Date -Format 'HH:mm:ss'), $c.Count, $gb, $ageMin, $n, $spxDone) -ForegroundColor $color
    if ($spxDone -ge 3) {
        Write-Host "SPX COMPLETE - small roots may still be running. Tell Claude to merge." -ForegroundColor Green
    }
    Start-Sleep -Seconds 60
}
