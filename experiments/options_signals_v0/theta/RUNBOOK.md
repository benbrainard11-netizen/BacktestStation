# ThetaData — setup & run

## Done for you (no login needed)
- [x] **Theta Terminal JAR** downloaded → `ThetaTerminal.jar` (v3, 11.5 MB)
- [x] **Java 21** installed (`C:\Program Files\Microsoft\jdk-21.0.11.10-hotspot\`)
- [x] **`creds.txt`** template + **`start_terminal.ps1`** launcher (Java path baked in)
- [x] **`.gitignore`** so the JAR + creds never get committed
- [x] **GEX puller** written → `../gex_pull.py`  ·  **API probe** → `../theta_check.py`

## You do (after subscribing to Options Pro, ~$160/mo)
1. **Fill `creds.txt`** — line 1 = your ThetaData email, line 2 = password.
2. **Start the Terminal** (leave it running in its own window):
   ```
   powershell -ExecutionPolicy Bypass -File experiments\options_signals_v0\theta\start_terminal.ps1
   ```
   (or `cd` into this folder and `java -jar ThetaTerminal.jar`)
3. **Probe the API + paste me the output:**
   ```
   backend\.venv\Scripts\python.exe experiments\options_signals_v0\theta_check.py
   ```
   This pings v2 (25510) and v3 (25503); whichever returns data tells me the exact endpoints.
4. I lock in `gex_pull.py`, then we pull (1-yr test first, then full history):
   ```
   backend\.venv\Scripts\python.exe experiments\options_signals_v0\gex_pull.py SPX 2025-01-01 2026-06-01
   ```
5. Repeat the pull for **NDX / RUT / DJX** → then I build the cross-asset GEX-divergence test + the
   gamma-regime / zero-gamma conditioner on the proven reclaim edge, with real multi-year OOS.
