# Server Deployment — BacktestStation + research_sidecar on ben-247

End-to-end recipe for getting the full stack (BacktestStation backend
+ frontend + research_sidecar trio) running 24/7 on the server, with
Tailscale-only access for Ben/Elijah devices.

> **Status:** draft. The pieces have all been verified individually
> on dev PCs but the full server install has not been performed yet.
> Treat each step as "verify before relying on."

---

## 1. Process inventory

Five services live on `ben-247`. All are Python `uvicorn` or `python
scripts/...` processes — no Node service in the recommended path.

| # | Service | Repo | Entry point | Port | Purpose |
|---|---|---|---|---|---|
| 1 | `backteststation-api` | BacktestStation | `python -m uvicorn app.main:app` (run from `backend/`) | **8000** | FastAPI: backtest engine, /api/* endpoints, eventually serves the static frontend |
| 2 | `sidecar-worker` | InSyncTradeBot | `python research_sidecar/scripts/run_worker.py` | — | Polls sources, ingests, scores ideas |
| 3 | `sidecar-discord` | InSyncTradeBot | `python research_sidecar/scripts/run_discord_bot.py` | — | Slash commands + Phase E interactive buttons |
| 4 | `sidecar-api` | InSyncTradeBot | `python research_sidecar/scripts/run_http_api.py` | **9000** | BacktestStation bridge HTTP API |
| 5 | `trading-bot` *(existing)* | InSyncTradeBot | as today | — | Untouched by this work |

**Total new long-running processes vs. today: 4** (the `trading-bot`
is unchanged).

## 2. One-time setup

### 2a. Repos

```powershell
# As user `Husky`, somewhere reasonable on D: or C:.
cd C:\
git clone https://github.com/benbrainard11-netizen/BacktestStation.git
git clone https://github.com/HuskyLimited/InSyncTradeBot.git
```

If the trading bot is already cloned, skip the second one and just
`git pull` on it.

### 2b. Python deps

Both repos have `requirements.txt`. Install into shared venvs (or
per-repo venvs — your call). The minimal new deps land via:

```powershell
# BacktestStation
cd C:\BacktestStation\backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# research_sidecar (new fastapi + uvicorn additions)
cd C:\InSyncTradeBot\research_sidecar
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 2c. Frontend build

```powershell
cd C:\BacktestStation\frontend
npm ci
npm run build
```

Output lands in `frontend/.next/`. Phase G **does not require static
export** — the frontend is served by `next start` (process #6 below) or
left to a separate machine. See §6 for the static-export tradeoffs if
you want to drop the Node process.

### 2d. Postgres

The sidecar already runs against your existing Postgres. BacktestStation
uses a separate DB (or schema). Confirm:
- `research_sidecar/.env` → `DATABASE_URL` points at the sidecar DB.
- `BacktestStation/backend/.env` → BacktestStation's own DB.

Do **not** share DB users between the two — V1 separation guarantee.

### 2e. Tailscale

Get the server's Tailscale IP:

```powershell
tailscale ip -4
```

Note this address — call it `<TS_IP>` below. Bind everything that
should be reachable from your laptop / Elijah's PC to this IP.

## 3. Environment files

### 3a. BacktestStation backend `.env`

```
DATABASE_URL=postgresql://user:pass@localhost:5432/backteststation
DATA_ROOT=D:\bts_data
GIT_SHA=auto
```

Tailscale binding for the API process happens at uvicorn launch
(§4), not in this file.

### 3b. research_sidecar `.env`

```
DATABASE_URL=postgresql+asyncpg://sidecar:pass@localhost:5432/research_sidecar
DISCORD_BOT_TOKEN=...
DISCORD_GUILD_ID=...
DISCORD_ALERT_CHANNEL_ID=...
ANTHROPIC_API_KEY=...
EXTRACTION_MODE=hybrid

# Phase C — HTTP API binding
HTTP_API_HOST=<TS_IP>
HTTP_API_PORT=9000

# Phase E — Discord button → BacktestStation handoff
BACKTESTSTATION_API_URL=http://localhost:8000/api
BACKTESTSTATION_PUBLIC_URL=http://<TS_IP>:8000
DEFAULT_BACKTEST_STRATEGY_NAME=composable
DEFAULT_BACKTEST_STRATEGY_VERSION_ID=1
```

Important: `HTTP_API_HOST` is the **Tailscale IP**, not `127.0.0.1`,
or your laptop won't reach the API. Discord-bot and worker don't bind
to anything; they only make outbound connections.

## 4. NSSM service definitions

[NSSM](https://nssm.cc/) is the recommended Windows service manager.
The trading bot already uses it; reuse the same install.

### 4a. BacktestStation API (port 8000, Tailscale-bound)

```powershell
nssm install backteststation-api `
    "C:\BacktestStation\backend\.venv\Scripts\python.exe" `
    "-m" "uvicorn" "app.main:app" `
    "--host" "<TS_IP>" `
    "--port" "8000"
nssm set backteststation-api AppDirectory "C:\BacktestStation\backend"
nssm set backteststation-api AppStdout "C:\BacktestStation\backend\logs\api.out.log"
nssm set backteststation-api AppStderr "C:\BacktestStation\backend\logs\api.err.log"
nssm set backteststation-api AppEnvironmentExtra "PYTHONUNBUFFERED=1"
nssm set backteststation-api Start SERVICE_AUTO_START
nssm start backteststation-api
```

### 4b. Sidecar HTTP API (port 9000, Tailscale-bound)

```powershell
nssm install sidecar-api `
    "C:\InSyncTradeBot\research_sidecar\.venv\Scripts\python.exe" `
    "C:\InSyncTradeBot\research_sidecar\scripts\run_http_api.py"
nssm set sidecar-api AppDirectory "C:\InSyncTradeBot\research_sidecar"
nssm set sidecar-api AppStdout "C:\InSyncTradeBot\research_sidecar\logs\api.out.log"
nssm set sidecar-api AppStderr "C:\InSyncTradeBot\research_sidecar\logs\api.err.log"
nssm set sidecar-api AppEnvironmentExtra "PYTHONUNBUFFERED=1"
nssm set sidecar-api Start SERVICE_AUTO_START
nssm start sidecar-api
```

The script reads `HTTP_API_HOST` from `.env` — no `--host` arg needed.

### 4c. Sidecar worker

```powershell
nssm install sidecar-worker `
    "C:\InSyncTradeBot\research_sidecar\.venv\Scripts\python.exe" `
    "C:\InSyncTradeBot\research_sidecar\scripts\run_worker.py"
nssm set sidecar-worker AppDirectory "C:\InSyncTradeBot\research_sidecar"
nssm set sidecar-worker Start SERVICE_AUTO_START
nssm start sidecar-worker
```

### 4d. Sidecar Discord bot

```powershell
nssm install sidecar-discord `
    "C:\InSyncTradeBot\research_sidecar\.venv\Scripts\python.exe" `
    "C:\InSyncTradeBot\research_sidecar\scripts\run_discord_bot.py"
nssm set sidecar-discord AppDirectory "C:\InSyncTradeBot\research_sidecar"
nssm set sidecar-discord Start SERVICE_AUTO_START
nssm start sidecar-discord
```

## 5. Frontend hosting

Two paths. Pick one.

### 5a. `next start` (recommended for now)

Add a sixth NSSM service:

```powershell
nssm install backteststation-frontend `
    "C:\Program Files\nodejs\node.exe" `
    "C:\BacktestStation\frontend\node_modules\next\dist\bin\next" "start" `
    "--hostname" "<TS_IP>" "--port" "3000"
nssm set backteststation-frontend AppDirectory "C:\BacktestStation\frontend"
nssm set backteststation-frontend AppEnvironmentExtra `
    "BACKEND_URL=http://localhost:8000" `
    "SIDECAR_URL=http://localhost:9000"
nssm set backteststation-frontend Start SERVICE_AUTO_START
nssm start backteststation-frontend
```

Browse from your laptop:
```
http://<TS_IP>:3000
```

The Next process proxies `/api/*` → `localhost:8000` and `/api/sidecar/*`
→ `localhost:9000` per `next.config.mjs` rewrites.

### 5b. Static export served by FastAPI (deferred)

Cleaner topology (one less process, single port), but our dynamic
routes (`/backtests/[id]`, `/strategies/[id]/build`) need either
`generateStaticParams` or a refactor to `?id=N` query params. Save
this for a later cleanup; **5a is the working setup today.**

## 6. Verification

After all services are running:

```powershell
# All services up?
nssm status backteststation-api
nssm status backteststation-frontend
nssm status sidecar-api
nssm status sidecar-worker
nssm status sidecar-discord

# Backend health (from server itself)
curl http://localhost:8000/api/health
curl http://localhost:9000/health

# Same from your laptop (over Tailscale)
curl http://<TS_IP>:8000/api/health
curl http://<TS_IP>:9000/health
curl http://<TS_IP>:3000
```

End-to-end smoke test:

1. From your laptop, open `http://<TS_IP>:3000/inbox`. You should
   see ideas the worker has scored.
2. Click **Backtest** on a promising idea. The Backtests page opens
   with a "from idea #N" badge in the modal.
3. Submit. Watch the run appear in the table with a "from #N" chip.
4. Open Discord. The high-score embed should have `[🧪 Backtest now]`
   `[⏭️ Skip]` `[📖 Open]` buttons.

## 7. Day-to-day ops

**Pull new code + restart everything:**
```powershell
cd C:\BacktestStation && git pull
cd C:\BacktestStation\frontend && npm ci && npm run build
cd C:\InSyncTradeBot && git pull

nssm restart backteststation-api
nssm restart backteststation-frontend
nssm restart sidecar-api
nssm restart sidecar-worker
nssm restart sidecar-discord
```

**Tail logs:**
```powershell
Get-Content -Tail 50 -Wait C:\BacktestStation\backend\logs\api.err.log
```

**Stop everything (e.g. Postgres maintenance):**
```powershell
nssm stop sidecar-discord
nssm stop sidecar-worker
nssm stop sidecar-api
nssm stop backteststation-frontend
nssm stop backteststation-api
```

## 8. Known gaps

- Static frontend export — see §5b. Eventual cleanup item.
- No reverse proxy / TLS. Tailscale is the perimeter; this is fine
  for two devices, would not be fine for public exposure.
- No log rotation on the NSSM `AppStdout` files. They grow forever;
  add a scheduled task or set NSSM rotation flags if you care.
- Postgres isn't a service we manage here; assumed already running.

## 9. Security boundary

- `--host <TS_IP>` means uvicorn won't accept connections from the
  LAN, only from devices on your tailnet. Belt + suspenders against
  accidental public exposure.
- The sidecar HTTP API has **no auth**. The Tailscale ACL is the only
  authentication boundary. If anything sensitive ever lands in
  `/ideas/{id}/result` payloads, revisit this.
- The trading bot is untouched — no code from this stack reaches it.
