# bsdata — BacktestStation cloud warehouse client

Read parquet partitions from Ben's BacktestStation R2 mirror, cached
locally, with the same loader API the backend uses internally.

```python
from bsdata import load_bars, load_tbbo, load_mbp1, get_inventory

# What's in the warehouse?
inv = get_inventory()
print(inv.symbols())  # ['ES.c.0', 'NQ.c.0', 'RTY.c.0', 'YM.c.0']
print(inv.date_range(schema="ohlcv-1m", symbol="NQ.c.0"))

# 1m bars (resampled to 5m at read time)
df = load_bars(symbol="NQ.c.0", start="2026-04-01", end="2026-04-25", timeframe="5m")

# Raw TBBO (top-of-book trades)
df = load_tbbo(symbol="NQ.c.0", start="2026-04-24", end="2026-04-25")

# Raw MBP-1
df = load_mbp1(symbol="NQ.c.0", start="2026-04-24", end="2026-04-25")
```

First call for a given (symbol, date) downloads the parquet from R2 to
the local cache. Subsequent calls hit the cache directly — full disk
speed, no network. Cache lives at `~/.bsdata/cache/` by default; override
with `BS_R2_CACHE_ROOT`.

## Setup (collaborator side)

You'll need:

1. The BacktestStation repo cloned on your machine (the loader imports
   `app.data.reader` for type unity — schema drift is impossible because
   there's exactly one parquet-reading codepath everywhere).
2. R2 credentials from Ben (sent via Signal — never in chat or email).
3. Python ≥ 3.11.

```powershell
git clone <BacktestStation repo URL>
cd BacktestStation
python -m venv .venv
.\.venv\Scripts\Activate.ps1

pip install -e .\backend
pip install -e .\client\bsdata

# R2 credentials (Ben sends these)
$env:BS_R2_BUCKET     = "bsdata-prod"
$env:BS_R2_ENDPOINT   = "https://<account-id>.r2.cloudflarestorage.com"
$env:BS_R2_ACCESS_KEY = "<reader access key>"
$env:BS_R2_SECRET     = "<reader secret>"

# Verify
python -c "from bsdata import get_inventory; inv = get_inventory(); print(inv.symbols())"
```

For persistent setup, save the env vars to your User scope:

```powershell
[Environment]::SetEnvironmentVariable("BS_R2_BUCKET",     "bsdata-prod",                                     "User")
[Environment]::SetEnvironmentVariable("BS_R2_ENDPOINT",   "https://<account-id>.r2.cloudflarestorage.com",   "User")
[Environment]::SetEnvironmentVariable("BS_R2_ACCESS_KEY", "<reader access key>",                             "User")
[Environment]::SetEnvironmentVariable("BS_R2_SECRET",     "<reader secret>",                                 "User")
```

## Cache behavior

- Default location: `~/.bsdata/cache/` (override via `BS_R2_CACHE_ROOT`).
- Layout mirrors the warehouse Hive partitioning, so cached reads go
  through the same `LocalStorage` codepath the backend uses internally.
- No cache eviction yet (Tier 1). Manage manually:
  `Remove-Item -Recurse ~\.bsdata\cache` to nuke; subsequent calls
  re-download from R2.
- Atomic writes: in-flight downloads land at `*.part` and are renamed
  on completion, so a half-downloaded file never appears as cached.

## Performance notes

- First call for N partitions = N HTTP GETs to R2. R2 has zero egress
  fees but each GET is one round-trip — for wide backtests (months of
  data, many symbols) the initial pull is network-bound.
- Subsequent calls = native disk speed. A 30-day NQ.c.0 1m backtest
  re-runs in seconds against cache.
- Parquet column pruning still works after caching — same code path as
  reading from `BS_DATA_ROOT` directly.

## What's NOT in scope (Tier 1)

- No write-back. R2 is read-only from the client side.
- No automatic cache eviction.
- No CLI yet — Python API only.
- No schema vendoring — requires the BacktestStation repo to be present.
- No auth proxy — credentials are static R2 API tokens scoped to the
  bucket. Tier 2 will add per-session presigned URLs once there are 3+
  external users.

See `docs/R2_SETUP.md` in the BacktestStation repo for the bucket setup
that produced the credentials you're using.
