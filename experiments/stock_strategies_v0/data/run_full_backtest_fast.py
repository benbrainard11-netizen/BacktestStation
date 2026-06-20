"""Fast driver for the full-universe intraday breakout backtest.

Reuses run_intraday_entry's EXACT logic (load_daily / run_setup / summarize) but parallelizes the
~182k per-setup minute reads across threads. The original main() is single-threaded and the work is
IO-bound (reading 182k tiny parquets one at a time was running for hours). run_setup is pure -- it
reads the shared daily dict D read-only and its own minute file, returns a dict -- so threading is
safe and gives identical results, just ~15x faster. Threads (not processes) so D (~1GB) is shared,
and pyarrow releases the GIL during the actual read.

Run with backend\\.venv\\Scripts\\python.exe -u (unbuffered).
"""

from __future__ import annotations

import importlib.util
import os
import time
from concurrent.futures import ThreadPoolExecutor

import pandas as pd

RIE = r"C:\Users\benbr\BacktestStation\experiments\stock_strategies_v0\unified_v0\run_intraday_entry.py"
_spec = importlib.util.spec_from_file_location("rie", RIE)
rie = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rie)

WORKERS = 24


def run_pass(D, jobs, target_R=None):
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        res = list(ex.map(lambda td: rie.run_setup(D, td[0], td[1], target_R), jobs))
    return pd.DataFrame([r for r in res if r is not None])


def main():
    t0 = time.time()
    print("loading daily (scoped to setup tickers)...", flush=True)
    D = rie.load_daily()
    samp = pd.read_parquet(rie.POLY / "minute_sample_manifest.parquet")
    jobs = list(zip(samp["ticker"], samp["date"].astype(int)))
    print(f"setups: {len(jobs):,}  workers={WORKERS}  (daily load {time.time() - t0:.0f}s)", flush=True)

    t1 = time.time()
    R = run_pass(D, jobs)
    act = set(samp[samp["active"]]["ticker"])
    R["active"] = R["tkr"].isin(act)
    R["yr"] = R["date"] // 10000
    R.to_parquet(rie.OUT / "intraday_entry_results_full.parquet")
    print(f"\n=== PRIMARY: 1m level-cross + {rie.K_ATR}xATR stop + chandelier let-run ===", flush=True)
    print(
        f"   ({len(R):,}/{len(jobs):,} setups usable)  [primary pass {time.time() - t1:.0f}s]\n", flush=True
    )
    rie.summarize(R, "ALL")
    rie.summarize(R[R.active], "active only")
    rie.summarize(R[~R.active], "DELISTED only")
    print(flush=True)
    for y in sorted(R["yr"].unique()):
        rie.summarize(R[R.yr == y], f"year {y}")

    if os.environ.get("RUN_GRID"):  # the 3R/5R/10R grid is 3 extra full passes; skip unless asked
        print("\n=== exit-rule grid (ALL setups) ===", flush=True)
        rie.summarize(R, "chandelier(3xATR)")
        for tr in (3, 5, 10):
            rr = run_pass(D, jobs, target_R=tr)
            rie.summarize(rr, f"fixed target {tr}R")

    mfe = R["mfe"]
    print(
        f"\nMFE: median {mfe.median():+.1f}R | p90 {mfe.quantile(.9):+.1f}R | "
        f">=10R {(mfe >= 10).mean() * 100:.1f}% | >=20R {(mfe >= 20).mean() * 100:.1f}%",
        flush=True,
    )
    print(f"READ: total {time.time() - t0:.0f}s", flush=True)


if __name__ == "__main__":
    main()
