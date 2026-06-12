"""Autopsy the 29 wall-race trades before believing +0.21R (n tiny, gap-artifact risk)."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

MODULE = Path(__file__).resolve().parent
REPO = MODULE.parents[1]
sys.path.insert(0, str(MODULE))
sys.path.insert(0, str(REPO / "experiments" / "btc_model_v0"))
from model_wf import run_wf  # noqa: E402
from wall_race import build_race, trade_sim  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")


def main() -> int:
    r = build_race()
    y = r["y_race"]
    geo = ["pos", "dist_c_rv", "dist_p_rv", "width_rv"]
    pg, _ = run_wf(r[geo], y, shuffle_target=False)
    mask = pg.notna() & y.notna()
    tr = trade_sim(pg, r, mask)
    tr = tr.set_index("d").join(r[["pos", "y_race", "entry", "cw", "pw", "close_d"]])
    tr["year"] = pd.DatetimeIndex(tr.index).year
    tr["side"] = (pg[tr.index] > 0).map({True: "long->cw", False: "short->pw"})
    tr["beyond_wall_at_open"] = (tr["entry"] >= tr["cw"]) | (tr["entry"] <= tr["pw"])
    tr["tgt_dist_pct"] = (tr["cw"] - tr["entry"]).where(
        pg[tr.index] > 0, tr["entry"] - tr["pw"]
    ) / tr["entry"]
    print(
        tr[
            [
                "side",
                "pos",
                "net_r",
                "y_race",
                "beyond_wall_at_open",
                "tgt_dist_pct",
                "year",
            ]
        ]
        .round(3)
        .to_string()
    )
    print(
        "\nby outcome:",
        tr.groupby("y_race")["net_r"].agg(["count", "mean"]).round(3).to_dict(),
    )
    print(
        "by year:",
        tr.groupby("year")["net_r"].agg(["count", "mean"]).round(3).to_dict(),
    )
    print("beyond-wall-at-open:", int(tr["beyond_wall_at_open"].sum()))
    clean = tr[~tr["beyond_wall_at_open"] & (tr["pos"] > 0.02) & (tr["pos"] < 0.98)]
    print(
        f"CLEAN subset (inside range, not through wall): n={len(clean)}, "
        f"mean net R {clean['net_r'].mean():+.3f}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
