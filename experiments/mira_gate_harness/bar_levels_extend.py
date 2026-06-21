"""6-month extension of the bar-only families (daily_gap / prev_mid / month_hl).
Jan probe: daily_gap +1.21 (4/4), prev_mid +0.40 (16), month_hl -0.21 (5) — settle at scale.
Importing bar_levels_test applies its _build_level_specs injection (module-level patch).

Run: backend/.venv/Scripts/python.exe experiments/mira_gate_harness/bar_levels_extend.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import bar_levels_test as BL  # noqa: E402  (applies the level injection on import)

H, RR, G = BL.H, BL.RR, BL.G
WINDOWS = [("train_bars", "2026-02-06", "2026-05-20"), ("holdout_bars", "2026-05-21", "2026-06-05")]


def main() -> int:
    gate = G.Gate()
    allnew = []
    for name, s, e in WINDOWS:
        ds = H.build_dataset(name, s, e)
        ds["trigger_ts_utc"] = pd.to_datetime(ds["trigger_ts_utc"], utc=True)
        ds["p"] = gate.score(ds)
        gt = (ds[ds.p >= gate.threshold].sort_values(["trigger_ts_utc", "trigger_id"], kind="stable")
              .groupby(H.OPP, sort=False).head(1).copy())
        new = gt[gt["level_family"].astype(str).isin(BL.NEW_FAMS)].copy()
        print(f"[{name}] candidates={len(ds)} gated={len(gt)} new-family={len(new)}", flush=True)
        if len(new):
            comp = RR.compute(new.drop(columns=["p"], errors="ignore"))
            new["realized_r"] = comp["realized_r"].to_numpy()
            allnew.append(new)
    jan = pd.read_parquet(H.DATA / "jan_bars.parquet")
    jan["trigger_ts_utc"] = pd.to_datetime(jan["trigger_ts_utc"], utc=True)
    jan["p"] = gate.score(jan)
    jg = (jan[jan.p >= gate.threshold].sort_values(["trigger_ts_utc", "trigger_id"], kind="stable")
          .groupby(H.OPP, sort=False).head(1))
    allnew.append(jg[jg["level_family"].astype(str).isin(BL.NEW_FAMS)])
    aw = pd.concat(allnew, ignore_index=True)
    aw["rr"] = pd.to_numeric(aw["realized_r"], errors="coerce")
    print(f"\n=== BAR FAMILIES, Jan-Jun (frozen gate; baseline +0.576) ===")
    for f in BL.NEW_FAMS:
        print(f"  {f:12s} {BL.st(aw[aw['level_family'].astype(str) == f]['rr'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
