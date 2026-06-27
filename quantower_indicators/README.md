# InSync Quantower Indicators

Custom C# Quantower indicators that overlay InSync order-flow + market-state onto live charts.
They read the local monitor API on `127.0.0.1:9100` (gamma/options levels, exhaustion model)
and the chart's own Rithmic L2/tape (order flow).

- **InSyncOrderflow** — real MBO order flow: resting **walls** (`wall <size> ×<orders>`, teal = bid/bull-limit /
  orange = ask/sell-limit), **on-candle fill markers** (`+N` teal = a bull-limit hit, `-N` orange = a sell-limit hit,
  at the price+candle it filled), a bottom **"pulled / min"** strip (red = wall size cancelled),
  **absorption/iceberg** (aggressor-colored), **sweeps**, **trapped traders**, trade bubbles (gated to wall hits),
  exhaustion-model overlay (NQ), and a market-state panel (gamma + vol). Walls/fills arrive over a **real-time push
  stream** (long-poll `/api/monitor/iceberg-flow/wait`) with a 0.25s file-poll fallback.
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
- `detector/iceberg_flow.py` — the MBO order-by-order detector that produces the walls/fills/flow. It tails the
  live Rithmic MBO JSONL, reconstructs the per-order book, and (a) writes `D:\data\heartbeat\iceberg_flow.json`
  and (b) PUBLISHES on ZMQ `tcp://127.0.0.1:5862` for the real-time stream. Runs as service `InsyncIcebergFlow`
  on the live box (out of `C:\Users\benbr\mbo_analysis\`). Kept here for version-control/backup.
- The **real-time stream** also needs the long-poll endpoint `/api/monitor/iceberg-flow/wait` — that lives in the
  `:9100` monitor API (`InsyncAPP_ben_merge/services/backtest/app/api/monitor.py`, service `MiraMonitorApi`), NOT in
  this repo. Without it (or if the detector isn't publishing) the indicator auto-falls back to the 0.25s file-poll.
