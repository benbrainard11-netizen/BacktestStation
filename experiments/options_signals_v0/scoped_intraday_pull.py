"""Scoped intraday options puller (Ben's spec, 2026-06-16).

Per (root, trading-day, expiration <= DTE_MAX): pull intraday greeks at IVL, keep only strikes within
+-BAND of that day's spot, and write ONE CLEAN parquet per (root, date):
    out/intraday/root=<ROOT>/date=<YYYYMMDD>.parquet
queryable directly by (root, date) -- no hash-keyed shard scanning.

Why fetch-all-then-filter: ThetaData bulk_hist has NO strike-range param (verified), so each request
returns the full expiration chain; we band-filter at write so DISK stays light (~57GB NDX+SPX) even
though the fetch is heavy. Fetch is per-(day, exp) so each request is bounded (no monster all-expiry call).

Resumable: skips any (root,date) already written. Recent-first. Shard by day across terminals.
Columns kept: date, ms_of_day, strike, right, expiration, bid, ask, underlying_price, implied_vol,
delta, theta, vega, rho (gamma computed from IV at build time; OI is a SEPARATE pull, prior-day pairing).

Run: THETA_PORT=25510 python scoped_intraday_pull.py NDXP 2025-05-01 2026-06-30 0 3
"""
from __future__ import annotations

import os

os.environ.setdefault("THETA_TIMEOUT", "180")
os.environ.setdefault("THETA_RETRIES", "2")

import subprocess
import sys
import time
from pathlib import Path

import pandas as pd
import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
import theta_store as TS  # noqa: E402
from gex_pull import _ymd  # noqa: E402

# --- self-heal: heavy intraday fetches wedge the terminal ~hourly; restart THIS shard's terminal ---
_PORT = os.environ.get("THETA_PORT", "25510")
_CFG = rf"C:\Users\benbr\ThetaData\ThetaTerminal\config_{int(_PORT) - 25510}.properties"
_JAVA = r"C:\Program Files\Microsoft\jdk-21.0.11.10-hotspot\bin\java.exe"
_TDIR = Path(__file__).resolve().parent / "theta"
_DETACHED = 0x00000008 | 0x08000000


def _term_ok() -> bool:
    try:
        return requests.get(f"http://127.0.0.1:{_PORT}/v2/list/roots/option", timeout=8).status_code == 200
    except Exception:
        return False


def _restart_terminal() -> bool:
    key = f"config_{int(_PORT) - 25510}"
    subprocess.run(["powershell", "-NoProfile", "-Command",
                    f"Get-CimInstance Win32_Process -Filter \"Name='java.exe'\" | "
                    f"Where-Object {{ $_.CommandLine -like '*{key}*' }} | "
                    f"ForEach-Object {{ Stop-Process -Id $_.ProcessId -Force }}"], capture_output=True)
    time.sleep(4)
    subprocess.Popen([_JAVA, "-jar", str(_TDIR / "ThetaTerminal.jar"), "--config", _CFG,
                      "--creds-file", str(_TDIR / "creds.txt")], cwd=str(_TDIR), creationflags=_DETACHED)
    for _ in range(24):
        time.sleep(5)
        if _term_ok():
            return True
    return False


def _fetch_resilient(**params):
    """fetch with up to 3 terminal-restarts on failure; returns df or None."""
    for attempt in range(4):
        try:
            return TS.fetch("bulk_hist/option/greeks", **params)
        except Exception:
            if attempt < 3:
                _restart_terminal()
    return None

ROOT = sys.argv[1]
START = sys.argv[2]
END = sys.argv[3]
SHARD = int(sys.argv[4]) if len(sys.argv) > 4 else 0
NSHARDS = int(sys.argv[5]) if len(sys.argv) > 5 else 1
IVL = int(os.environ.get("IVL", "60000"))
BAND = float(os.environ.get("BAND", "0.06"))
DTE_MAX = int(os.environ.get("DTE_MAX", "45"))
OUT = Path(__file__).resolve().parent / "out" / "intraday"
CAL = Path(r"D:\data\processed\bars\timeframe=1m\symbol=NQ.c.0")  # trading calendar
KEEP = ["date", "ms_of_day", "strike", "right", "expiration", "bid", "ask",
        "underlying_price", "implied_vol", "delta", "theta", "vega", "rho"]


def trading_days(s: int, e: int) -> list[int]:
    out = []
    for p in CAL.glob("date=*"):
        d = int(p.name.split("=")[1].replace("-", ""))
        if s <= d <= e:
            out.append(d)
    return sorted(out, reverse=True)  # recent-first


def main() -> int:
    s, e = _ymd(START), _ymd(END)
    days = trading_days(s, e)[SHARD::NSHARDS]
    if not _term_ok():
        _restart_terminal()
    allexps = []
    for _a in range(4):
        try:
            allexps = sorted(int(x) for x in TS.expirations(ROOT))
            break
        except Exception:
            _restart_terminal()
    print(f"[{ROOT} s{SHARD}/{NSHARDS}] {len(days)} trading days, IVL={IVL}, band=±{BAND:.0%}, DTE<={DTE_MAX}", flush=True)
    wrote = 0
    for di, d in enumerate(days):
        dmax = _ymd(pd.Timestamp(str(d)) + pd.Timedelta(days=DTE_MAX))
        exps = [x for x in allexps if d <= x <= dmax]
        if not exps:
            continue
        ddir = OUT / f"root={ROOT}" / f"date={d}"
        for exp in exps:
            outf = ddir / f"exp={exp}.parquet"      # one file per expiration -> progress survives wedges
            if outf.exists():
                continue
            df = _fetch_resilient(root=ROOT, exp=exp, start_date=d, end_date=d, ivl=IVL)
            if df is None or df.empty:
                continue
            spot = float(pd.to_numeric(df["underlying_price"], errors="coerce").median())
            if not (spot > 0):
                continue
            band = df[(df["strike"] >= spot * (1 - BAND)) & (df["strike"] <= spot * (1 + BAND))]
            if len(band):
                ddir.mkdir(parents=True, exist_ok=True)
                tmp = outf.with_suffix(".tmp.parquet")
                band[[c for c in KEEP if c in band.columns]].to_parquet(tmp)
                tmp.replace(outf)
                wrote += 1
        if (di + 1) % 5 == 0 or wrote:
            print(f"[{ROOT} s{SHARD}] thru {d} ({di+1}/{len(days)} days): {wrote} exp-files written", flush=True)
    print(f"[{ROOT} s{SHARD}] DONE: {wrote} exp-files written", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
