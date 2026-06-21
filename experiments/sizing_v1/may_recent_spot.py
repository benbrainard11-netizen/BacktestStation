"""Recent-window spot replays (the only OOS-clean recent day + a couple recent DOWN days).

Data ends 2026-05-22, so the live window (~May 23-Jun 5) is unreplayable. This checks:
  * 2026-05-21 (post-training OOS, up day): does detection/gate yield candidates? long/short/longs-only.
  * 2026-05-15, 05-12 (recent DOWN days, IN-SAMPLE for the gate): DETECTION yield by direction
    (candidate counts are model-independent, so in-sample is fine for COUNTS) -> tests whether a
    recent down day suppresses LONG reclaim setups (regime hypothesis) or not (mean-reversion).

Per-day: post_sweep_smt detection counts L/S, and gated+dedup counts L/S (gated only OOS-valid on 05-21).
No retuning, no live connection.
"""
from __future__ import annotations

import datetime as dt
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
sys.path.insert(0, r"C:\Users\benbr\BacktestStation\live_engine\engine")
import detect as D  # noqa: E402
import gate as G  # noqa: E402
import live_runner as lr  # noqa: E402

OPP = "combined.sweep_setup_event_id"
SYMS = ["ES.c.0", "NQ.c.0", "RTY.c.0", "YM.c.0"]
DAYS = [(dt.date(2026, 5, 21), "OOS up day"),
        (dt.date(2026, 5, 15), "DOWN day (in-sample gate)"),
        (dt.date(2026, 5, 12), "DOWN day (in-sample gate)")]


def one(symbol, day, g, thr):
    c = D.compute_candidates(symbol, day, day, sweep_quality=None)
    if c is None or len(c) == 0:
        return (0, 0, 0, 0, 0, 0)
    c["trigger_ts_utc"] = pd.to_datetime(c["trigger_ts_utc"], utc=True)
    pss = c[(c["trigger_type"] == "post_sweep_smt") & (c["smt_anchor_side"].isin(["low", "high"]))
            & c["trigger_price"].notna()].copy()
    if len(pss) == 0:
        return (0, 0, 0, 0, 0, 0)
    detL = int((pss.smt_anchor_side == "low").sum()); detS = int((pss.smt_anchor_side == "high").sum())
    pss["p"] = g.score(pss)
    gated = pss[pss["p"] >= thr].copy()
    if OPP in gated.columns and len(gated):
        gated = gated.sort_values(["trigger_ts_utc", "trigger_id"], kind="stable").groupby(OPP, sort=False).head(1)
    gL = int((gated.smt_anchor_side == "low").sum()); gS = int((gated.smt_anchor_side == "high").sum())
    # realistic engine entries via replay_session
    try:
        st = lr.replay_session(symbol, day, sweep_quality=None)
        ent = int(st["entries"])
    except Exception:
        ent = -1
    return (detL, detS, gL, gS, ent, len(pss))


def main() -> int:
    g = G.Gate(); thr = g.threshold
    print(f"gate threshold = {thr:.4f}\n")
    for day, tag in DAYS:
        tot = np.zeros(5, dtype=int)
        print(f"=== {day} [{tag}] ===")
        for s in SYMS:
            detL, detS, gL, gS, ent, npss = one(s, day, g, thr)
            tot += np.array([detL, detS, gL, gS, max(ent, 0)])
            print(f"   {s:8s} detection L/S={detL}/{detS}  gated+dedup L/S={gL}/{gS}  replay_entries={ent}")
        print(f"   TOTAL    detection L/S={tot[0]}/{tot[1]}  gated L/S={tot[2]}/{tot[3]}  "
              f"longs_only_gated={tot[2]}  replay_entries={tot[4]}\n", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
