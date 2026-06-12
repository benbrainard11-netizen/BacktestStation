"""Pull full CME BTC futures 1m bar history (module-local scratch; proper lake ingest
via the 247 box later if the module survives). Cost-checked, $10 abort budget.

Run: backend/.venv/Scripts/python.exe experiments/btc_edge_v0/pull_bars.py
"""

import sys
from pathlib import Path

import databento as db

sys.stdout.reconfigure(encoding="utf-8")
OUT = Path(__file__).resolve().parent / "data" / "btc_1m.parquet"

client = db.Historical()
ARGS = dict(
    dataset="GLBX.MDP3",
    symbols=["BTC.c.0"],
    stype_in="continuous",
    schema="ohlcv-1m",
    start="2017-12-01",
    end="2026-06-10",
)
cost = client.metadata.get_cost(**ARGS)
print(f"quoted cost: ${cost:.2f}")
if cost > 10.0:
    print("ABORT — over $10 budget")
    sys.exit(1)
df = client.timeseries.get_range(**ARGS).to_df()
print("rows:", len(df), "| range:", df.index.min(), "->", df.index.max())
df.to_parquet(OUT)
print(f"saved {OUT}")
