"""LEVEL x CONFIRMATION decomposition (Ben's question): does each level family have its own
best confirmation type/TF? Pooled bar-confirmation was breakeven -- this splits it per family to
find the specific level x confirmation pairs that actually separate winners.

DESIGN (odd years) exploration; the strongest sign-consistent pairs get ONE-SHOT on even years.
Multiple-testing aware: 9 families x {ob,fvg} x {1m,5m,15m} = lots of cells; treat design as
hypothesis generation, the even-year one-shot as the test.
"""
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
df = pd.read_parquet(HERE / "runs" / "bar_confirm.parquet")
src = pd.read_parquet(HERE / "runs" / "legal_bars_full.parquet")
key = ["symbol", "decision_ts_utc", "level_price", "side"]
df = df.merge(src[key + ["depth_tk", "wait_s"]].drop_duplicates(key), on=key, how="left")
df = df[df["trail_2R"].abs() <= 5].copy()
df["yr"] = pd.to_datetime(df["session_date"]).dt.year
DESIGN = {2015, 2017, 2019, 2021, 2023, 2025}
des = df[df["yr"].isin(DESIGN)].copy()
combo = (des["depth_tk"] > 8) & (des["wait_s"] >= 300)

CONFIRMS = ["ob_confirm_5m", "fvg_5m", "ob_confirm_15m", "fvg_15m", "ob_confirm_1m", "fvg_1m"]
fams = sorted(des["level_family"].unique())


def mr(x):
    x = pd.to_numeric(x, errors="coerce").dropna()
    return (len(x), x.mean(), (x > 0).mean()) if len(x) else (0, float("nan"), float("nan"))


print("=== LEVEL x CONFIRMATION (DESIGN odd yrs, COMBO depth>8+wait>=5m). meanR when confirmed=1 ===")
print(f"{'family':16s} {'base':>9s} " + " ".join(f"{c.replace('_confirm',''):>11s}" for c in CONFIRMS))
for fam in fams:
    sub = des[combo & (des["level_family"] == fam)]
    bn, bm, _ = mr(sub["trail_2R"])
    row = f"{fam:16s} {bm:+.3f}({bn:4d}) "
    for c in CONFIRMS:
        n, m, w = mr(sub[sub[c] == 1]["trail_2R"])
        row += f"{m:+.2f}({n:3d}) " if n >= 15 else f"   --({n:3d}) "
    print(row)

print("\n=== STRONGEST sign-consistent (family,confirm) pairs on DESIGN (combo, confirmed meanR>0, n>=25) ===")
cands = []
for fam in fams:
    sub = des[combo & (des["level_family"] == fam)]
    for c in CONFIRMS:
        n, m, w = mr(sub[sub[c] == 1]["trail_2R"])
        nn, nm, _ = mr(sub[sub[c] == 0]["trail_2R"])
        if n >= 25 and m > 0 and (m - nm) > 0:
            cands.append((fam, c, n, m, w, m - nm))
for fam, c, n, m, w, lift in sorted(cands, key=lambda t: -t[3]):
    print(f"  {fam:16s} {c:16s} confirmed +{m:.3f} win{100*w:.0f}% n={n}  lift +{lift:.3f}")
print("\n-> the positive pairs above are the ONE-SHOT candidates for even-year validation.")
