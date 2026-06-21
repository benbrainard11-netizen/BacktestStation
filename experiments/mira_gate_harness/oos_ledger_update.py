"""A4: the auto-accruing fresh-OOS ledger. Run weekly (or any time): pulls new days,
materializes, scans SMT, builds the window, scores the FROZEN champion + overlay variants,
appends one row per (window, variant) to runs/oos_ledger.csv. The un-overfittable scoreboard.

Usage: backend/.venv/Scripts/python.exe experiments/mira_gate_harness/oos_ledger_update.py
       [--start 2026-06-10] [--end <last complete weekday, default: yesterday>]
"""
from __future__ import annotations

import argparse
import datetime as dt
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PY = str(ROOT / "backend" / ".venv" / "Scripts" / "python.exe")
RUNS = HERE / "runs"


def run(desc, args, env=None):
    print(f"--- {desc}", flush=True)
    e = {**os.environ, **(env or {})}
    r = subprocess.run([PY] + args, env=e)
    if r.returncode != 0:
        raise SystemExit(f"step failed: {desc} (rc={r.returncode})")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="2026-06-10")
    ap.add_argument("--end", default=(dt.date.today() - dt.timedelta(days=1)).isoformat())
    args = ap.parse_args()
    s, e = args.start, args.end
    if s > e:
        print("nothing new to cover")
        return 0
    end_excl = (dt.date.fromisoformat(e) + dt.timedelta(days=1)).isoformat()
    name = f"oos_{s.replace('-', '')}_{e.replace('-', '')}"
    smt_db = HERE / "data" / f"{name}_smt5m.sqlite"

    run("pull MBO + mirror", [str(ROOT / "experiments/sizing_v1/pull_recent_mbo_databento.py"),
                              "--start", s, "--end", end_excl, "--cost-threshold-usd", "100", "--mirror"])
    run("pull MBP-1", [str(HERE / "pull_mbp1.py"), "--start", s, "--end", end_excl])
    run("materialize trading days", [str(ROOT / "backend/scripts/materialize_mbo_trading_day_cache.py"),
                                     "--start", s, "--end", e, "--allow-missing-sources"])
    run("bars from MBP-1", ["-c", f"""
import sys, datetime as dt, pandas as pd
sys.path.insert(0, r'{ROOT / 'backend'}')
from app.ingest.parquet_mirror import _compute_1m_bars
from pathlib import Path
RAW = Path(r'D:/data/raw/databento/mbp-1'); BARS = Path(r'D:/data/processed/bars/timeframe=1m')
d = dt.date.fromisoformat('{s}')
while d <= dt.date.fromisoformat('{e}'):
    for sym in ('ES.c.0','NQ.c.0','YM.c.0','RTY.c.0'):
        src = RAW / f'symbol={{sym}}' / f'date={{d}}' / 'part-000.parquet'
        dst = BARS / f'symbol={{sym}}' / f'date={{d}}' / 'part-000.parquet'
        if src.exists() and not dst.exists():
            df = pd.read_parquet(src, columns=['ts_event','action','price','size'])
            df['ts_event'] = pd.to_datetime(df['ts_event'], utc=True)
            b = _compute_1m_bars(df, sym)
            if len(b): dst.parent.mkdir(parents=True, exist_ok=True); b.to_parquet(dst, index=False)
    d += dt.timedelta(days=1)
print('bars done')
"""])
    run("SMT 5m scan", [str(HERE / "ledger_smt_scan.py"), s, end_excl, str(smt_db)])
    run("build + score + append", ["-c", f"""
import os, sys, datetime as dt
import pandas as pd
os.environ['BACKTESTSTATION_BACKEND'] = r'{ROOT / 'live_engine' / 'vendor'}'
os.environ['MIRA_SMT_DB'] = r'{smt_db}'
sys.path.insert(0, r'{HERE}'); sys.path.insert(0, r'{ROOT / 'live_engine' / 'engine'}')
import harness as H, realized_r as RR, gate as G
ds = H.build_dataset('{name}', '{s}', '{e}')
ds['trigger_ts_utc'] = pd.to_datetime(ds['trigger_ts_utc'], utc=True)
g = G.Gate(); ds['p'] = g.score(ds)
gt = (ds[ds.p >= g.threshold].sort_values(['trigger_ts_utc','trigger_id'], kind='stable')
      .groupby(H.OPP, sort=False).head(1).copy())
comp = RR.compute(gt.drop(columns=['p'], errors='ignore'))
gt['realized_r'] = comp['realized_r'].to_numpy()
ds.loc[gt.index, 'realized_r'] = gt['realized_r']; ds.to_parquet(H.DATA / '{name}.parquet', index=False)
gt['rr'] = pd.to_numeric(gt['realized_r'], errors='coerce'); gt = gt[gt.rr.notna()]
et = gt['trigger_ts_utc'].dt.tz_convert('America/New_York'); hr = et.dt.hour + et.dt.minute/60
asia_cut = (gt['level_family'].astype(str) == 'asia_session') & (hr >= 10)
rows = []
def add(variant, sub):
    r = sub['rr']
    rows.append(dict(window='{name}', start='{s}', end='{e}', variant=variant, n=len(r),
                     meanR=round(float(r.mean()),3) if len(r) else None,
                     sumR=round(float(r.sum()),1) if len(r) else None,
                     ts=dt.datetime.now().isoformat(timespec='seconds')))
add('champion', gt); add('champion_asia10cut', gt[~asia_cut])
p = r'{RUNS / 'oos_ledger.csv'}'
df = pd.DataFrame(rows)
import os.path
df.to_csv(p, mode='a', header=not os.path.exists(p), index=False)
print(df.to_string(index=False))
"""])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
