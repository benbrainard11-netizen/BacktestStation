"""Iteration 3 event study: each trigger separately AND in confluence.

The honest first readout of the trigger->seek-the-wall idea. For each slice reports:
  n, reach% (hit wall before stop), geom_prior% (driftless gambler's-ruin baseline:
  stop/(target+stop)), edge = reach - prior (THE number: does the trigger beat
  geometry at reaching the wall?), mean signed R (net), gross R, and a fade check
  (reach of the opposite direction). Not a gate — a diagnosis.

Run: backend\\.venv\\Scripts\\python.exe experiments\\fuhhhhh\\event_study.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common as C

OUT = Path(__file__).resolve().parent / "out"


def row(df: pd.DataFrame, label: str) -> dict:
    if len(df) < 20:
        return {"slice": label, "n": len(df), "note": "thin"}
    prior = df["stop_dist_pts"] / (df["target_dist_pts"] + df["stop_dist_pts"])
    by_month = df.groupby(df["date"].str.slice(0, 7))["r_signed"].mean()
    return {
        "slice": label, "n": len(df),
        "reach%": round(df["reached"].mean() * 100, 1),
        "prior%": round(prior.mean() * 100, 1),
        "edge": round((df["reached"].mean() - prior.mean()) * 100, 1),
        "meanR": round(df["r_signed"].mean(), 3),
        "grossR": round((df["r_signed"] + C.COST_PTS / df["stop_dist_pts"]).mean(), 3),
        "R_d1": round(df["r_signed_d1"].dropna().mean(), 3) if df["r_signed_d1"].notna().any() else np.nan,
        "mo+": f"{int((by_month > 0).sum())}/{len(by_month)}",
        "tgt_pts": round(df["target_dist_pts"].median(), 1),
        "stop_pts": round(df["stop_dist_pts"].median(), 1),
    }


def main() -> int:
    tag = sys.argv[1] if len(sys.argv) > 1 else "v3"
    df = pd.read_parquet(OUT / f"events_{tag}.parquet")
    print(f"=== event study: {tag} ===")
    out = [row(df, "ALL events")]
    out.append(row(df[df["dir"] == 1], "  dir=UP"))
    out.append(row(df[df["dir"] == -1], "  dir=DOWN"))
    # each trigger involved (may co-fire), and each trigger SOLO (confluence==1)
    for k in ("sweep", "smt", "flow"):
        out.append(row(df[df[f"fired_{k}"]], f"{k} (involved)"))
        out.append(row(df[df[f"fired_{k}"] & (df["confluence"] == 1)], f"  {k} solo"))
    out.append(row(df[df["confluence"] >= 2], "confluence>=2"))
    out.append(row(df[df["confluence"] == 3], "confluence==3"))
    # resolved-only reach (exclude EOD timeouts) to isolate the race itself
    resolved = df[df["mins_to_resolve"].notna() | (df["y"] != 2)]
    out.append(row(df[df["y"] != 2], "resolved (no EOD timeout)"))

    rep = pd.DataFrame(out).set_index("slice")
    print(rep.to_string())
    print(f"\nNOTE: edge = reach% - prior%. Positive => trigger beats driftless geometry "
          f"at reaching the wall. timeout share = {(df['y'] == 2).mean():.1%}")

    # fade check: if edge is negative, would betting AGAINST the trigger have reached
    # its (opposite) barrier? approximate via stop-hit rate vs its own prior
    stop_prior = (df["target_dist_pts"] / (df["target_dist_pts"] + df["stop_dist_pts"])).mean()
    print(f"fade check: stop-hit rate {(~df['reached'] & (df['y'] != 2)).mean():.1%} "
          f"vs stop prior {stop_prior:.1%}")

    (OUT / f"report_{tag}_eventstudy.md").write_text(f"# {tag} event study\n\n" + rep.to_string(), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
