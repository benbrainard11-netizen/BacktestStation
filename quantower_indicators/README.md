# InSync Quantower Indicators

Custom C# Quantower indicators that overlay InSync order-flow + market-state onto live charts.
They read the local monitor API on `127.0.0.1:9100` (gamma/options levels, exhaustion model)
and the chart's own Rithmic L2/tape (order flow).

- **InSyncOrderflow** — real MBO order flow: resting **walls** (with order count `×N`),
  **absorption/iceberg** (aggressor-colored: teal = bid/buyer-absorbing, orange = ask/seller-absorbing),
  **sweeps**, **trapped traders** (red = trapped longs / green = trapped shorts), trade bubbles
  (gated to wall hits), exhaustion-model overlay (NQ), and a market-state panel (gamma + vol).
- **InSyncMarketState** — gamma/options levels: call wall, put wall, zero-gamma flip, GEX walls, max pain.

## Requirements
- **Quantower v1.146.13.** The `.csproj` files reference Quantower's DLLs by absolute path
  (`C:\Quantower\TradingPlatform\v1.146.13\bin\...`). A different version → edit those HintPaths
  **and** `$qtVersion` in `build-deploy.ps1`. A DLL built against one Quantower version may not
  load on another.
- **.NET 10 SDK** (projects target `net10.0`). On the live box it lives at `%LOCALAPPDATA%\Microsoft\dotnet`.

## Build + deploy (recommended)
```powershell
powershell -ExecutionPolicy Bypass -File build-deploy.ps1
```
Builds both in Release and copies the DLLs into `...\Scripts\Indicators\InSync\`.
**Restart Quantower** afterward — it only loads indicators at startup.

## Notes
- The indicators are display-only off `:9100` + the chart feed; no credentials, nothing outbound.
- Backend that feeds them (`:9100` monitor API, the MBO iceberg/trap detector) lives elsewhere in
  this repo / on the live box — these are just the chart-side renderers.
