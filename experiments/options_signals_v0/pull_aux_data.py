"""Pull the light auxiliary datasets that ARE free on the sub: vol indices (VIX/VXN/...) EOD,
index EOD levels, and per-stock dividends. (Index INTRADAY is paywalled -> 471; rates absent.)
All tiny. Stored under out/{vol_indices,index_eod,dividends}/.
Run: THETA_PORT=25510 python pull_aux_data.py
"""

from __future__ import annotations

import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parent))
import theta_store as TS  # noqa: E402

OUT = Path(__file__).resolve().parent / "out"
VOL = ["VIX", "VXN", "VXD", "RVX", "VIX9D", "VIX1D", "VVIX"]  # VXN=Nasdaq vol, VXD=Dow, RVX=Russell
IDX = ["NDX", "SPX", "RUT", "DJX"]
STK = ["NVDA", "AAPL", "MSFT", "TSLA", "GOOGL", "AMZN", "META", "AVGO"]
EOD = ["ms_of_day", "open", "high", "low", "close", "volume", "date"]


def grab(ep, root, sub, **kw):
    try:
        d = TS.fetch_flat(ep, root=root, start_date=20120101, end_date=20261231, **kw)
    except Exception as e:
        print(f"  {root}: FAIL {type(e).__name__}")
        return
    if not len(d):
        print(f"  {root}: empty")
        return
    keep = [c for c in EOD if c in d.columns] if "stock/dividend" not in ep else list(d.columns)
    (OUT / sub).mkdir(parents=True, exist_ok=True)
    d[keep].to_parquet(OUT / sub / f"{root}.parquet")
    yrs = sorted(set(str(int(x))[:4] for x in d["date"])) if "date" in d.columns else []
    print(f"  {root}: {len(d)} rows  {yrs[:1]+yrs[-1:]}")


print("=== vol indices (EOD) ===")
for r in VOL:
    grab("hist/index/eod", r, "vol_indices")
print("=== index EOD levels ===")
for r in IDX:
    grab("hist/index/eod", r, "index_eod")
print("=== dividends ===")
for t in STK:
    grab("hist/stock/dividend", t, "dividends")
# intraday vol test (VIX) — if allowed, note it for a follow-up chunked pull
try:
    di = TS.fetch_flat("hist/index/ohlc", root="VIX", start_date=20260609, end_date=20260609, ivl=60000)
    print(
        f"\nVIX intraday(1d) test: {len(di)} rows -> {'AVAILABLE (can pull intraday vol)' if len(di) else 'empty'}"
    )
except Exception as e:
    print(f"\nVIX intraday test: blocked ({type(e).__name__}) — EOD vol only")
