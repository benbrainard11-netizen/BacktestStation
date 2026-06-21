"""Dump raw walls per day, all definitions, to see what's actually going on."""
import sys
from pathlib import Path
import pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent))
import common as C

v2 = pd.read_parquet(Path(__file__).resolve().parent / "out" / "walls_v2.parquet").set_index("date")
old = pd.read_parquet(C.WALLS_DEEP).set_index("date")
intr = pd.read_parquet(C.INTRADAY_GEX)
op = intr.sort_values("ms_of_day").groupby("date").first()
la = intr.sort_values("ms_of_day").groupby("date").last()

# pick overlap dates spread across the recent window
common = sorted(set(v2.index) & set(old.index) & set(op.index))
picks = common[::max(1, len(common) // 10)][:10]
print(f"{'date':>9} {'spot':>7} | {'OLD cw':>7} {'OLD pw':>7} | {'v2 cw':>7} {'v2 pw':>7} | "
      f"{'intrO cw':>8} {'intrO pw':>8} | {'intrL cw':>8} {'intrL pw':>8}")
for d in picks:
    s = v2.loc[d, "spot"]
    print(f"{d:>9} {s:>7.0f} | {old.loc[d,'call_wall']:>7.0f} {old.loc[d,'put_wall']:>7.0f} | "
          f"{v2.loc[d,'call_wall']:>7.0f} {v2.loc[d,'put_wall']:>7.0f} | "
          f"{op.loc[d,'call_wall']:>8.0f} {op.loc[d,'put_wall']:>8.0f} | "
          f"{la.loc[d,'call_wall']:>8.0f} {la.loc[d,'put_wall']:>8.0f}")
print("\nOLD=walls_deep(max-per-side)  v2=walls_v2(net-gamma argmax)  intrO/L=intraday panel open/last")
