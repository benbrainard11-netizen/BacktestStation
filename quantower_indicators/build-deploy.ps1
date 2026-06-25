# Build both InSync Quantower indicators and deploy the DLLs into Quantower.
# Requires: .NET 10 SDK + Quantower (default v1.146.13).
#   powershell -ExecutionPolicy Bypass -File build-deploy.ps1
$ErrorActionPreference = "Stop"
$root = $PSScriptRoot
$qtVersion = "v1.146.13"                                  # <-- match your Quantower version
$qtDir = "C:\Quantower\TradingPlatform\$qtVersion"
$deploy = Join-Path $qtDir "bin\Scripts\Indicators\InSync"

# projects target net10.0 -> prefer the .NET 10 SDK (per-user install), else PATH
$dn = Join-Path $env:LOCALAPPDATA "Microsoft\dotnet\dotnet.exe"
if (-not (Test-Path $dn)) { $dn = "dotnet" }

if (-not (Test-Path $qtDir)) { throw "Quantower $qtVersion not found at $qtDir. Install it or edit `$qtVersion above (and the HintPaths in each .csproj)." }
New-Item -ItemType Directory -Force -Path $deploy | Out-Null

foreach ($proj in @("InSyncOrderflow", "InSyncMarketState")) {
    $csproj = Join-Path $root "$proj\$proj.csproj"
    Write-Host "building $proj ..."
    & $dn build $csproj -c Release -v m
    if ($LASTEXITCODE -ne 0) { throw "$proj build failed" }
    Copy-Item (Join-Path $root "$proj\bin\Release\$proj.dll") (Join-Path $deploy "$proj.dll") -Force
    Write-Host "  deployed -> $deploy\$proj.dll"
}
Write-Host "done. Restart Quantower to load the updated indicators."
