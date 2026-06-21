"""F7 check: how much do same-bar (entry-bar) resolutions move the numbers?"""
import sys
from pathlib import Path
import pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent))
OUT = Path(__file__).resolve().parent / "out"

for tag in ("v3", "v3_s025"):
    df = pd.read_parquet(OUT / f"events_{tag}.parquet")
    sb = (df["mins_to_resolve"] == 0).mean()
    excl = df[df["mins_to_resolve"] != 0]
    print(f"{tag}: same-bar share={sb:.1%}  meanR all={df['r_signed'].mean():+.3f}  "
          f"excl-samebar={excl['r_signed'].mean():+.3f}")
    ss = df[df["fired_sweep"] & (df["confluence"] == 1)]
    sse = ss[ss["mins_to_resolve"] != 0]
    print(f"   sweep-solo meanR={ss['r_signed'].mean():+.3f} (n={len(ss)})  "
          f"excl-samebar={sse['r_signed'].mean():+.3f} (n={len(sse)})")
    ssd = ss[ss["dir"] == -1]
    print(f"   sweep-solo SHORT meanR={ssd['r_signed'].mean():+.3f} (n={len(ssd)})")
