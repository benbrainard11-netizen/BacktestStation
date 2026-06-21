"""NASDAQ event study: does an NQ trigger seek the prior-day NDX gamma wall?

Mirrors event_study_typed.py's reach/edge/R blocks on the events_ndx schema (simple
sweep+SMT triggers, no typed tags). R is NET of NQ cost; grossR adds it back. The
"edge" column = reach% minus the geometry prior (stop_dist / (stop+target)) — a trigger
only adds value if it beats that baseline. Descriptive, not a gate.

Run: backend\\.venv\\Scripts\\python.exe experiments\\fuhhhhh\\event_study_ndx.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common as C

OUT = Path(__file__).resolve().parent / "out"
pd.set_option("display.width", 220)


def row(df: pd.DataFrame, label: str) -> dict:
    if len(df) < 25:
        return {"slice": label, "n": len(df), "note": "thin"}
    prior = df["stop_dist_pts"] / (df["target_dist_pts"] + df["stop_dist_pts"])
    bymo = df.groupby(df["date"].str.slice(0, 7))["r_signed"].mean()
    return {"slice": label, "n": len(df),
            "reach%": round(df["reached"].mean() * 100, 1),
            "edge": round((df["reached"].mean() - prior.mean()) * 100, 1),
            "meanR": round(df["r_signed"].mean(), 3),
            "grossR": round((df["r_signed"] + C.COST_PTS_NQ / df["stop_dist_pts"]).mean(), 3),
            "R_d1": round(df["r_signed_d1"].dropna().mean(), 3) if df["r_signed_d1"].notna().any() else np.nan,
            "medR": round(df["r_signed"].median(), 3),
            "mo+": f"{int((bymo > 0).sum())}/{len(bymo)}"}


def block(title: str, rows: list[dict]) -> str:
    rep = pd.DataFrame(rows).set_index("slice")
    print(f"\n### {title}")
    print(rep.to_string())
    return f"\n### {title}\n{rep.to_string()}\n"


def main() -> int:
    fn = sys.argv[1] if len(sys.argv) > 1 else "events_ndx.parquet"
    df = pd.read_parquet(OUT / fn)
    out = [f"# NASDAQ event study ({fn})\n",
           f"events={len(df)}  days={df['date'].nunique()}  "
           f"range={df['date'].min()}..{df['date'].max()}  cost_pts_nq={C.COST_PTS_NQ:.3f}\n"]

    out.append(block("Triggers overall", [
        row(df, "ALL"), row(df[df.dir == 1], "  UP"), row(df[df.dir == -1], "  DOWN"),
        row(df[df.fired_sweep], "sweep (any)"), row(df[df.fired_smt], "smt (any)"),
        row(df[df.fired_sweep & (df.confluence == 1)], "sweep solo"),
        row(df[df.fired_sweep & (df.confluence == 1) & (df.dir == 1)], "sweep solo LONG"),
        row(df[df.fired_sweep & (df.confluence == 1) & (df.dir == -1)], "sweep solo SHORT"),
        row(df[df.fired_smt & (df.confluence == 1)], "smt solo"),
        row(df[df.confluence == 2], "sweep+smt confluence"),
    ]))

    # entry-time robustness for the headline cell
    ss = df[df.fired_sweep & (df.confluence == 1)]
    out.append(block("sweep-solo by entry hour (ET)", [
        row(ss[(ss.ms >= h * 3600_000) & (ss.ms < (h + 1) * 3600_000)], f"{h:02d}:00")
        for h in range(9, 16)]))

    # per-month detail for sweep-solo SHORT (the ES winner) and LONG
    for lbl, sub in [("sweep-solo SHORT", ss[ss.dir == -1]), ("sweep-solo LONG", ss[ss.dir == 1])]:
        if len(sub) >= 25:
            bymo = sub.groupby(sub["date"].str.slice(0, 7)).agg(
                n=("r_signed", "size"), meanR=("r_signed", "mean"), reach=("reached", "mean"))
            bymo["meanR"] = bymo["meanR"].round(3); bymo["reach"] = (bymo["reach"] * 100).round(1)
            print(f"\n### {lbl} — per month"); print(bymo.to_string())
            out.append(f"\n### {lbl} — per month\n{bymo.to_string()}\n")

    (OUT / "report_ndx_eventstudy.md").write_text("\n".join(out), encoding="utf-8")
    print(f"\nreport -> {OUT / 'report_ndx_eventstudy.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
