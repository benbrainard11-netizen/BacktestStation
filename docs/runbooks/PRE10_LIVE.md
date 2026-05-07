# Pre10 v04 live runbook — TPT funded, 1 MNQ

The procedure for going live on the Pre10 v04 strategy on the TPT $25K
funded Rithmic account, sized at **1 MNQ** per the overnight 2026-05-06
Monte Carlo (92.3% Phase-1 clear with `skip_2023` filter at $80/trade).
The bot has been running paper-mode on ben-247 since this session
shipped. This runbook covers the Sunday-afternoon flip from paper to
live, the during-session monitoring path, and rollback.

**Hard rule:** never run §2 (live install) without first passing §1
(dry-run). Cred / system_name / contract bugs are 100% recoverable
before you submit a single order. Once §2 is live, every bug costs at
least $80.

## 1. Pre-flight — Sunday afternoon, before 5pm CT

All steps run on **ben-247**.

### 1.1 Set Rithmic credentials at User scope

`User`-scope so they survive reboot but are never logged or pushed.
Get the values from the TPT account email — pwd is the *funded* one,
not the demo. `RITHMIC_SERVER` is **not** "Rithmic Paper Trading" —
TPT funded uses a different system name.

```powershell
[Environment]::SetEnvironmentVariable('RITHMIC_USERNAME','<TPT user>','User')
[Environment]::SetEnvironmentVariable('RITHMIC_PASSWORD','<TPT password>','User')
[Environment]::SetEnvironmentVariable('RITHMIC_SERVER','<system name from TPT email>','User')
```

`RITHMIC_CONTRACT` defaults to `MNQM6` (MNQ Jun 2026, current front
month). Override only if TPT shows a different format (`MNQ-06-26`,
`MNQM26`, etc.):

```powershell
[Environment]::SetEnvironmentVariable('RITHMIC_CONTRACT','<symbol>','User')
```

### 1.2 Pull the latest code

```powershell
cd C:\Users\benbr\FractalAMD-
git pull --ff-only origin align-with-plugin-2026-04-28-pm
```

### 1.3 Dry-run — validates auth without trading

Open a **new** PowerShell so the env vars get picked up. Then:

```powershell
cd C:\Users\benbr\FractalAMD-
py production/pre10_live_runner.py --rithmic-dry-run
```

**Expected output within ~30 seconds:**

```
[DRY RUN] connecting to Rithmic ...
Rithmic connected as account TPT-XXXXXX
[DRY RUN] OK — account_id=TPT-XXXXXX contract=MNQM6 server='<server>'
[DRY RUN] disconnected cleanly
```

Exit code 0.

**If anything fails — STOP.** Do not proceed to §2. Report the exact
error message. Most likely: wrong system_name (look for "no accounts"
or "account_id field not received"), wrong creds (auth failure), or
network issue (timeout). Cred bugs are 100% recoverable here.

### 1.4 Confirm BacktestStation backend is reachable

Heartbeats post over Tailscale to benpc. From ben-247:

```powershell
Test-NetConnection 100.64.66.60 -Port 8000
```

`TcpTestSucceeded: True` is required. If False: benpc isn't reachable
on Tailscale; check `tailscale status` on both machines.

## 2. Live install

### 2.1 Edit the install script

```powershell
notepad C:\Users\benbr\FractalAMD-\production\install_pre10_service.ps1
```

Two lines at the top:

```powershell
$RunnerMode = 'paper'   # → change to 'live'
$Contracts  = 1         # confirm 1, not 2
```

After edit:

```powershell
$RunnerMode = 'live'
$Contracts  = 1
```

Save. Don't change anything else.

### 2.2 Re-run installer (Admin PowerShell)

```powershell
powershell -ExecutionPolicy Bypass -File C:\Users\benbr\FractalAMD-\production\install_pre10_service.ps1
```

The installer prints a yellow banner:

```
=== LIVE MODE ENABLED ===
  Server:   <your TPT server>
  Contract: MNQM6
  Size:     1 contract(s)
  User:     <your TPT user>
=========================
```

**Verify the banner before proceeding.** Wrong server → halt. Wrong
size → halt. Re-edit and re-run if anything's off.

### 2.3 Restart the service

```powershell
Restart-Service Pre10LiveRunner
```

### 2.4 Tail logs for the first 60 seconds

```powershell
sc.exe queryex Pre10LiveRunner
Get-Content D:\data\logs\pre10_live\runner.err.log -Tail 30 -Wait
```

Within 60 seconds you should see:

```
[LIVE] connecting to Rithmic …
Rithmic connected as account TPT-XXXXXX
[LIVE] Rithmic ready
[LIVE] preloading 1m bars + daily frame …
[LIVE] router model loaded
… bar processing …
```

If you see anything else (especially "halting", "rejected", "halt"),
fix before market opens. Reference §4 for rollback.

## 3. During-session monitoring

Watch from **benpc** browser at `http://localhost:3000/monitor` (or the
Tauri desktop app). What good looks like:

- **Live Bot panel:** `[LIVE] [running]` chips, balance $25,000, mode
  LIVE, contracts=1, position flat.
- **Heartbeat cadence strip:** all green cells (≤75s gaps).
- **Connection-quality chip** (header): "ok".
- **Halt history:** "0 halts in window" or empty.

What 9:45 ET fires (or doesn't) looks like:

- **Entry fires:** Open Position block appears with side/entry/stop,
  fill_state goes "pending" → "filled", contracts=1, MFE/MAE update
  per minute. Account profit and Today P&L track live.
- **Entry skipped (router gate):** A signal row may appear with
  `executed=false` and reason "router P_up=...". No position opens.
  This is normal — the router gates ~30% of signals.
- **No signal:** No row at all if the entry trigger never fires.
  Pre10 v04 fires 0–1 times per session; many days have nothing.

What an exit looks like:

- **Stop hit:** Rithmic's bracket auto-fills the stop. Engine emits
  ExitSignal with reason "stop_hit". Position block disappears.
- **Trail-50pct:** Engine emits TrailModification when MFE > 1R.
  Stop_price in panel updates. If stop hits, exit.
- **Time stop:** 30 minutes after entry. Engine emits ExitSignal,
  runner explicitly flattens via Rithmic. Position block disappears.

### Halts during session

If the panel goes `[halted]` (red chip), look at the halt_reason:

- "HALT.flag present": someone created `production/HALT.flag`. Remove
  it and `Restart-Service Pre10LiveRunner` if intentional.
- "$XXX daily soft loss …": $750 soft cap hit. Bot won't trade more
  today. Investigate, but no action needed if you accept the loss.
- "N consecutive losses": rare; review trade logs before un-halting.
- "TPT trail breached": catastrophic. Bot will flatten + halt. Manual
  recovery: cancel residual orders via Rithmic web, decide whether to
  cycle the account.
- "N consecutive heartbeat failures": telemetry to BS broken for ≥3
  minutes. Bot can't be observed → halts itself. Check Tailscale +
  BS backend on benpc, then `Restart-Service Pre10LiveRunner`.

## 4. Rollback

### Quick halt (1 step, no deploy)

```powershell
New-Item -ItemType File -Path C:\Users\benbr\FractalAMD-\production\HALT.flag
```

The runner picks this up on the next bar (≤60s) and halts. Existing
brackets stay on Rithmic — close them manually via TPT web if needed.

### Full revert to paper

1. Edit installer back to paper:
   ```powershell
   notepad C:\Users\benbr\FractalAMD-\production\install_pre10_service.ps1
   # Change $RunnerMode = 'live'  →  $RunnerMode = 'paper'
   ```
2. Re-run installer (Admin):
   ```powershell
   powershell -ExecutionPolicy Bypass -File C:\Users\benbr\FractalAMD-\production\install_pre10_service.ps1
   ```
3. `Restart-Service Pre10LiveRunner`. Banner should say "paper" not
   "LIVE MODE".
4. Confirm `[PAPER]` chip on /monitor.

### Service won't restart

```powershell
Get-Content D:\data\logs\pre10_live\runner.err.log -Tail 50
```

Most common: stale Rithmic session, missing env vars after a reboot
(rare — `User` scope persists), or the runner crashed during connect.
For Rithmic session: stop the service, wait 60s for Rithmic to time
the session out, restart.

## 5. Post-session checks

End of RTH (4pm ET):

- `/monitor` should show the day's trade(s) under "Recent signals" with
  `executed=true` chips.
- If a trade fired, the realized R should match what Rithmic shows.
  Material divergence (>0.10R) is a signal-engine vs broker-fill
  mismatch — flag it.
- Equity curve on /monitor: balance line should track actual TPT
  balance (off by trail-locked withdrawals if any).
- Cadence strip: should be solid green for the entire session. Any red
  cells = telemetry blip; investigate Tailscale.

End of week, if 5+ trades have fired:

- Compare actual Phase-1 progression vs the 92.3% MC expectation (the
  research fork's `phase2_1mnq_mc.md`). One week is small sample, but
  >2σ deviation either way warrants a closer look.
