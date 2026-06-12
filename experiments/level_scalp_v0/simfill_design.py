"""SIM-VENUE successor design study — stop/TP geometry under prop-sim fill mechanics.

Venue spec change (successor to the Phase 1 NULL, which was for real-FIFO CME):
prop-firm SIM engines grant limit fills from the price feed with no real queue —
entry fills at the level on touch/trade-at-price, stops fill AT the stop price
(no gap-through), targets fill on touch. The atlas EV frame approximates this:
  win  = +k when exit-side quote crosses target first (conservative for sim)
  loss = -(j + stress) flat (stress 0 = pure sim, 1 = one tick of sim slippage)
  neither = g_end. Net = - commission ticks.

DESIGN DATA: SELECTION window (2025) atlas only. The intact HOLDOUT (2026-04..06)
remains the successor's single confirmatory shot, AFTER Ben ground-truths his
platform's actual sim fill rule with live test orders. CONFIRMATION is partially
unblinded (Phase 1 cell aggregates) — usable only as a disclosed soft check.

Outputs per surviving cell: full (k,j) grid under sim fills, top configs by
SELECTION-AWARE p5 (best re-chosen inside each day resample — rule C20), the
high-RR (k >= 1.5j) subset, first-touch vs retest split, overshoot stop table.

Run: backend/.venv/Scripts/python.exe experiments/level_scalp_v0/simfill_design.py
Artifact: report/simfill_design.md
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from spec import GRID_TICKS, MODULE, OUT  # noqa: E402
from atlas_report import RTH, block_boot, comm_ticks, md_table  # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:  # noqa: BLE001
    pass

CELLS = [  # the 4 atlas survivors, frozen definitions
    ("P3", "ES.c.0", ["pdc"], ["on", "pre"], None),
    ("P6", "ES.c.0", ["round"], RTH, None),
    (
        "P7",
        "ES.c.0",
        ["pdh", "pdl", "onh", "onl"],
        RTH,
        lambda d: d["defend_sz_norm"] >= 2.0,
    ),
    ("P8", "RTY.c.0", ["round"], RTH, None),
]
STRESS = 1  # ticks of sim stop slippage assumed (0 would be the pure-sim fantasy)


def sim_ev_matrix(df: pd.DataFrame) -> tuple[np.ndarray, list[tuple[int, int]]]:
    pairs = [(k, j) for k in GRID_TICKS for j in GRID_TICKS]
    g_end = df["g_end"].to_numpy(float)
    cols = []
    for k, j in pairs:
        tw = df[f"t_win_{k}"].to_numpy(float)
        tl = df[f"t_loss_{j}"].to_numpy(float)
        win = ~np.isnan(tw) & (np.isnan(tl) | (tw < tl))
        loss = ~np.isnan(tl) & (np.isnan(tw) | (tl <= tw))
        cols.append(np.where(win, float(k), np.where(loss, -float(j + STRESS), g_end)))
    return np.column_stack(cols), pairs


def grid_table(df: pd.DataFrame, sym: str, label: str) -> tuple[pd.DataFrame, str]:
    ev, pairs = sim_ev_matrix(df)
    ct = comm_ticks(sym)
    net = ev - ct
    days = df["trading_day"].astype(str).to_numpy()
    means, best = block_boot(net, days)
    rows = []
    for i, (k, j) in enumerate(pairs):
        rows.append(
            {
                "k": k,
                "j": j,
                "rr": round(k / j, 2),
                "net": round(float(net[:, i].mean()), 2),
                "p5": round(float(np.percentile(means[:, i], 5)), 2),
                "win%": round(float((ev[:, i] == k).mean()), 2),
            }
        )
    g = pd.DataFrame(rows)
    sel_aware_p5 = float(np.percentile(best, 5))
    note = (
        f"{label}: n={len(df)}, days={df['trading_day'].nunique()}, "
        f"selection-aware p5 of BEST grid cell = {sel_aware_p5:+.2f} "
        f"(any single-cell p5 must beat this hurdle to be believed)"
    )
    return g, note


def main() -> int:
    at = {
        s: pd.read_parquet(OUT / f"atlas_touches_{s}.parquet")
        for s in ["ES.c.0", "RTY.c.0"]
    }
    lines = [
        "# Sim-venue design study — SELECTION (2025) only; holdout untouched",
        "",
        f"Loss model: stop fills at stop + {STRESS} tick (sim slippage); entry/TP at "
        "level/target on quote-cross (conservative for sim). Net of commission.",
        "",
    ]
    for cid, sym, fams, buckets, extra in CELLS:
        d = at[sym]
        m = d["family"].isin(fams) & d["tod_bucket"].isin(buckets)
        if extra is not None:
            m &= extra(d)
        sub = d[m]
        g, note = grid_table(sub, sym, cid)
        top = g.sort_values("p5", ascending=False).head(5)
        hi_rr = g[g["rr"] >= 1.5].sort_values("p5", ascending=False).head(5)
        lines += [
            f"## {cid} ({'+'.join(fams)} {sym})",
            "",
            note,
            "",
            "Top 5 by day-block p5:",
            md_table(top),
            "",
            "Top 5 high-RR (k >= 1.5j):",
            md_table(hi_rr),
            "",
        ]
        # first touch vs retest split at the cell's strongest simple config (8,8)
        ev88, _ = sim_ev_matrix(sub)
        col88 = [(k, j) for k in GRID_TICKS for j in GRID_TICKS].index((8, 8))
        for nm, mm in [
            ("first touch (n=1)", sub["touch_n"] == 1),
            ("retest (n>=2)", sub["touch_n"] >= 2),
        ]:
            if mm.sum() >= 50:
                lines += [
                    f"- (8,8) {nm}: net {float(ev88[mm.to_numpy(), col88].mean() - comm_ticks(sym)):+.2f} "
                    f"ticks (n={int(mm.sum())})"
                ]
        rej = sub[sub["rejected_8"] == True]  # noqa: E712
        if len(rej) >= 30:
            q = rej["overshoot_ticks"].quantile([0.5, 0.75, 0.9]).round(1).tolist()
            lines += [
                f"- overshoot through level before 8t rejection: med/p75/p90 = {q} "
                f"(a stop tighter than ~p75 gets swept on ~25%+ of good rejections)",
                "",
            ]
        else:
            lines += [""]
    report = "\n".join(lines)
    (MODULE / "report" / "simfill_design.md").write_text(report, encoding="utf-8")
    print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
