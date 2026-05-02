# Wire ben-247 to push to R2 — one-time setup

**What this does:** adds ben-247 (the live-collection node) to the same R2 bucket that benpc is already pushing to. After this, new TBBO captured by the live ingester each day flows to R2 within an hour, instead of waiting for the next benpc → R2 cycle (which is gated by Taildrop sync timing).

**Why bother:** today, live data path is `ben-247 → Taildrop → benpc → R2`. That introduces ~24h lag for new data to reach the cloud. Wiring ben-247 directly to R2 cuts the lag to ~1 hour.

**Time required:** ~10 min, all from ben-247 itself.

---

## Prerequisites

- You're at ben-247 (RDP, console, or after enabling Tailscale SSH per "Future" section below)
- R2 bucket `bsdata-prod` already exists (it does — benpc has been pushing to it since 2026-05-01)
- The same uploader token you've been using on benpc (the read-write one)

⚠️ **You're using the SAME uploader token, not a new one.** Don't create a third token; reuse `bsdata-uploader`. Hive partitioning prevents collisions between benpc and ben-247 uploads as long as their date ranges don't overlap (and even if they do, last-writer-wins on identical content is fine).

---

## Step 1 — Set the env vars on ben-247

Open **PowerShell as your normal user** (not Admin — User-scope env vars don't need elevation, and the existing setup pattern uses User-scope so the S4U scheduled task inherits them).

```powershell
[Environment]::SetEnvironmentVariable("BS_R2_BUCKET",     "bsdata-prod",                                                       "User")
[Environment]::SetEnvironmentVariable("BS_R2_ENDPOINT",   "https://ce39fd0a76dfeb63f9195bc09028c899.r2.cloudflarestorage.com", "User")
[Environment]::SetEnvironmentVariable("BS_R2_ACCESS_KEY", "<<<PASTE_UPLOADER_ACCESS_KEY_HERE>>>",                              "User")
[Environment]::SetEnvironmentVariable("BS_R2_SECRET",     "<<<PASTE_UPLOADER_SECRET_HERE>>>",                                  "User")
```

**Replace the `<<< ... >>>` placeholders with the values from your password manager BEFORE pressing Enter.** Don't paste this block back into chat after filling in the secrets (we already learned that lesson).

## Step 2 — Verify env vars stuck

Open a **new** PowerShell window (the one above won't see freshly-set vars):

```powershell
$env:BS_R2_BUCKET                       # should print: bsdata-prod
$env:BS_R2_ENDPOINT                     # should print the https://... URL
$env:BS_R2_ACCESS_KEY.Length            # should print 32
$env:BS_R2_SECRET.Length                # should print 64
```

If all four print expected values, env is wired up.

## Step 3 — Pull the latest code on ben-247

The R2 uploader code (`backend/app/ingest/r2_upload.py` + `r2_client.py` + `r2_partitions.py`) needs to exist on ben-247:

```powershell
cd C:\Users\benbr\BacktestStation
git pull origin main
```

If you haven't already pushed from benpc, do that first:
```powershell
# (on benpc)
cd C:\Users\benbr\BacktestStation
git push origin main
```

Then `git pull` on ben-247 picks it up.

## Step 4 — Sanity-check the uploader against R2

```powershell
cd C:\Users\benbr\BacktestStation\backend
.\.venv\Scripts\python.exe -m app.ingest.r2_upload --dry-run --limit 5
```

This walks ben-247's `D:\data` warehouse, validates the first 5 partitions, and reports without uploading anything. Expected: `validated=5 refused=0` (or fewer if ben-247 has fewer than 5 partitions in the read-side dirs).

If you see `refused=N` with `parquet read failed: Unable to merge`, see the note in `docs/OVERNIGHT_2026-05-01-PM.md` — that's a different issue, fixed in the latest code, but ben-247 needs to have pulled the fix.

## Step 5 — Register the scheduled task

Open **PowerShell as Administrator** on ben-247 (Win+X → Terminal (Admin)):

```powershell
cd C:\Users\benbr\BacktestStation
powershell -ExecutionPolicy Bypass -File scripts\install_scheduled_tasks.ps1
```

The script registers all 5 tasks (idempotent, uses `-Force`). Look for `BacktestStationR2Upload` in the summary table at the end. Its first fire will be at the next HH:15.

## Step 6 — Confirm it's running

After the next HH:15 fire (give it 5 min after that to start uploading):

```powershell
# Check task last result (0 = success, 267009 = "already running" which is fine after first fire)
Get-ScheduledTaskInfo BacktestStationR2Upload | Select LastRunTime, LastTaskResult, NextRunTime

# Check upload log
Get-Content 'D:\data\logs\r2_upload.log' -Tail 20

# Check inventory state from this machine
.\backend\.venv\Scripts\python.exe -c @'
from app.ingest.r2_client import make_s3_client, read_inventory
c, b = make_s3_client()
inv = read_inventory(c, b)
print(f'partitions in R2: {len(inv["partitions"]) if inv else 0}')
print(f'inventory generated_at: {inv["generated_at"] if inv else "(none)"}')
'@
```

You should see partitions in R2 grow over time as both benpc and ben-247 contribute. Both machines see the same inventory because it's a single shared `_inventory.json` at the bucket root.

---

## Coexistence with benpc's uploader

**Both machines push to the same bucket. That's intentional and safe:**

- Hive partitioning means each `(symbol, date, schema)` lands at one canonical key. If both machines have the same partition (e.g. NQ.c.0 2026-04-15 TBBO from a historical pull), last-writer-wins on identical content — no harm.
- The hourly schedule offset is HH:15 on both machines. They might race occasionally; the inventory-merge logic (kept_for_inventory + carried_over) handles this — neither machine's run will erase the other's contributions.
- The 2-hour `ExecutionTimeLimit` on each task means a runaway upload kills itself rather than blocking forever.

**If you want to specialize:**

- ben-247 only uploads new live data (typically <5 partitions/day): keep as-is, runs are short.
- benpc handles the deep historical archive (~127K partitions, weeks-long initial backfill): keep as-is.
- Both will converge on the same R2 state.

---

## Future: enable Tailscale SSH on ben-247

So future R2 setup work can happen remotely without needing your hands on ben-247. Run this once on ben-247:

```powershell
& "C:\Program Files\Tailscale\tailscale.exe" up --ssh
```

After that, from benpc you can run any command on ben-247 via:

```powershell
& "C:\Program Files\Tailscale\tailscale.exe" ssh insyncserver "<command>"
```

No password prompts because Tailnet ACLs handle auth (you own both devices). This unblocks future ops work without RDP.

---

## Tear-down

If you ever want to stop ben-247 from uploading (without losing benpc's uploader):

```powershell
Unregister-ScheduledTask -TaskName BacktestStationR2Upload -Confirm:$false
[Environment]::SetEnvironmentVariable("BS_R2_ACCESS_KEY", $null, "User")
[Environment]::SetEnvironmentVariable("BS_R2_SECRET",     $null, "User")
```

Leave bucket + endpoint vars in place if you might want bsdata reads from ben-247 later (those need the same env vars). Just nuking the secret credentials disables uploads while preserving the option to read.
