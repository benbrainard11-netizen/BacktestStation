"""Phase 0 step 3 — UNBLIND the atlas: cell statistics, primary-cell verdicts, retest table.

Statistical rules implemented here (PLAN §Non-negotiables C):
  C19 — only the 8 pre-registered PRIMARY cells carry kill/advance authority; their
        (k,j) is pre-specified per symbol (ES/YM/RTY (8,8), NQ (12,12)).
  C20 — exploratory cells use a SELECTION-AWARE bootstrap: the best (k,j) is re-chosen
        inside every day-block resample (reality-check); rankings use that p5.
  C21 — min-n gate (n>=200, days>=60) before any cell is ranked.
  C23 — headline numbers must survive BOTH a day-block and a level-block bootstrap
        (wider of the two reported as p5).
  Stop-wins-ties: equal first-passage times score as the loss.

EV per touch for fade with target k / stop j (ticks): win +k, loss -j, neither g_end;
net under maker wall (commission only) and taker wall (commission + cell median
touch-spread + 1 tick slip). This is a SCREENING metric — Phase 1 does honest fills.

Run: backend/.venv/Scripts/python.exe experiments/level_scalp_v0/atlas_report.py
Artifacts: out/atlas_cells.parquet, report/atlas_v0.md
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from spec import (
    COMMISSION_RT,
    GRID_TICKS,
    MODULE,
    OUT,
    POINT_VALUE,
    SYMBOLS,
    TICK,
)  # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:  # noqa: BLE001
    pass

RTH = ["open", "late_am", "lunch", "pm", "post"]
MIN_N, MIN_DAYS, N_BOOT = 200, 60, 1500
KJ = {"ES.c.0": (8, 8), "NQ.c.0": (12, 12), "YM.c.0": (8, 8), "RTY.c.0": (8, 8)}
PRIMARIES = [  # (name, symbol, families, buckets, extra_mask_fn)
    ("P1 gap_pdc ES open", "ES.c.0", ["gap_pdc"], ["open"], None),
    ("P2 premarket NQ open", "NQ.c.0", ["pmh", "pml"], ["open"], None),
    ("P3 pdc ES on+pre", "ES.c.0", ["pdc"], ["on", "pre"], None),
    ("P4 PDH/PDL NQ RTH", "NQ.c.0", ["pdh", "pdl"], RTH, None),
    ("P5 round NQ RTH", "NQ.c.0", ["round"], RTH, None),
    ("P6 round ES RTH", "ES.c.0", ["round"], RTH, None),
    (
        "P7 wall-extremes ES RTH",
        "ES.c.0",
        ["pdh", "pdl", "onh", "onl"],
        RTH,
        lambda d: d["defend_sz_norm"] >= 2.0,
    ),
    ("P8 round RTY RTH", "RTY.c.0", ["round"], RTH, None),
]


def comm_ticks(sym: str) -> float:
    return COMMISSION_RT / (TICK[sym] * POINT_VALUE[sym])


def md_table(df: pd.DataFrame) -> str:
    try:
        return df.to_markdown(index=False)
    except ImportError:
        return "```\n" + df.to_string(index=False) + "\n```"


def ev_matrix(df: pd.DataFrame) -> tuple[np.ndarray, list[tuple[int, int]]]:
    """Per-touch gross EV (ticks) for every (k, j) grid cell. Stop wins ties."""
    pairs = [(k, j) for k in GRID_TICKS for j in GRID_TICKS]
    g_end = df["g_end"].to_numpy(float)
    cols = []
    for k, j in pairs:
        tw = df[f"t_win_{k}"].to_numpy(float)
        tl = df[f"t_loss_{j}"].to_numpy(float)
        win = ~np.isnan(tw) & (np.isnan(tl) | (tw < tl))
        loss = ~np.isnan(tl) & (np.isnan(tw) | (tl <= tw))
        cols.append(np.where(win, float(k), np.where(loss, -float(j), g_end)))
    return np.column_stack(cols), pairs


def block_boot(ev: np.ndarray, blocks: np.ndarray, n_boot: int = N_BOOT, seed: int = 0):
    """Bootstrap mean EV per grid column, resampling whole blocks (days or level_keys).

    Returns (means[n_boot, n_cols], best_means[n_boot]) where best re-selects the max
    column INSIDE each resample (selection-aware, rule C20).
    """
    uniq, inv = np.unique(blocks, return_inverse=True)
    nb, nc = len(uniq), ev.shape[1]
    sums = np.zeros((nb, nc))
    cnts = np.zeros(nb)
    np.add.at(sums, inv, ev)
    np.add.at(cnts, inv, 1.0)
    rng = np.random.default_rng(seed)
    draws = rng.integers(0, nb, size=(n_boot, nb))
    tot = sums[draws].sum(axis=1)  # [n_boot, nc]
    n = cnts[draws].sum(axis=1)[:, None]
    means = tot / np.maximum(n, 1.0)
    return means, means.max(axis=1)


def cell_stats(df: pd.DataFrame, sym: str, kj: tuple[int, int] | None) -> dict:
    """Stats for one cell. kj fixed -> primary semantics; kj None -> selection-aware."""
    ev, pairs = ev_matrix(df)
    ct = comm_ticks(sym)
    taker_extra = float(df["spread_ticks"].median()) + 1.0
    days = df["trading_day"].astype(str).to_numpy()
    keys = df["level_key"].to_numpy()
    out = {
        "n": len(df),
        "days": int(df["trading_day"].nunique()),
        "comm_ticks": round(ct, 2),
        "taker_extra_ticks": round(taker_extra + ct, 2),
    }
    if kj is not None:
        col = pairs.index(kj)
        net = ev[:, [col]] - ct  # maker wall
        d_means, _ = block_boot(net, days)
        l_means, _ = block_boot(net, keys, seed=1)
        out.update(
            kj=f"{kj[0]}/{kj[1]}",
            ev_gross=float(ev[:, col].mean()),
            ev_net_maker=float(net.mean()),
            ev_net_taker=float((ev[:, col] - ct - taker_extra).mean()),
            p5_maker=float(min(np.percentile(d_means, 5), np.percentile(l_means, 5))),
            p95_maker=float(
                max(np.percentile(d_means, 95), np.percentile(l_means, 95))
            ),
        )
        out["pass_maker"] = out["p5_maker"] > 0
    else:
        net = ev - ct
        best_col = int(np.argmax(net.mean(axis=0)))
        _, d_best = block_boot(net, days)
        _, l_best = block_boot(net, keys, seed=1)
        out.update(
            kj=f"{pairs[best_col][0]}/{pairs[best_col][1]} (best)",
            ev_net_maker=float(net[:, best_col].mean()),
            ev_net_taker=float((net[:, best_col] - taker_extra).mean()),
            p5_maker=float(min(np.percentile(d_best, 5), np.percentile(l_best, 5))),
        )
        out["pass_maker"] = False  # exploratory cells never pass by themselves (C19)
    return out


def main() -> int:
    at = {s: pd.read_parquet(OUT / f"atlas_touches_{s}.parquet") for s in SYMBOLS}
    lines = ["# Atlas v0 — UNBLINDED (spec frozen at this run)", ""]

    lines += [
        "## Primary cells (sole gating authority; fixed (k,j); maker wall = commission only)",
        "",
    ]
    prim_rows = []
    for name, sym, fams, buckets, extra in PRIMARIES:
        d = at[sym]
        m = d["family"].isin(fams) & d["tod_bucket"].isin(buckets)
        if extra is not None:
            m &= extra(d)
        sub = d[m]
        st = {"cell": name, **cell_stats(sub, sym, KJ[sym])}
        prim_rows.append(st)
    prim = pd.DataFrame(prim_rows)
    lines += [md_table(prim), ""]
    n_pass = int(prim["pass_maker"].sum())
    lines += [
        f"**Primary verdict: {n_pass}/8 cells clear the maker wall at p5 "
        f"(day-block AND level-block, wider CI).**",
        "",
    ]

    lines += [
        "## Retest / overshoot table (stop-offset evidence; lit gap we now own)",
        "",
    ]
    rt = []
    for s, d in at.items():
        rej = d[d["rejected_8"] == True]  # noqa: E712
        if len(rej) == 0:
            continue
        rt.append(
            {
                "symbol": s,
                "n_rejected8": len(rej),
                "p_retest_2t": round(float(rej["retest_after_8"].mean()), 3),
                "overshoot_med": round(float(rej["overshoot_ticks"].median()), 1),
                "overshoot_p75": round(float(rej["overshoot_ticks"].quantile(0.75)), 1),
                "overshoot_p90": round(float(rej["overshoot_ticks"].quantile(0.90)), 1),
            }
        )
    lines += [md_table(pd.DataFrame(rt)), ""]

    lines += [
        "## Exploratory cells (selection-aware p5; NO gating power — rule C19/C20)",
        "",
    ]
    expl = []
    for s, d in at.items():
        d = d.copy()
        d["sess"] = np.where(d["tod_bucket"].isin(RTH), "rth", "on_pre")
        for (fam, sess), sub in d.groupby(["family", "sess"], observed=True):
            if len(sub) < MIN_N or sub["trading_day"].nunique() < MIN_DAYS:
                continue
            expl.append(
                {"symbol": s, "family": fam, "sess": sess, **cell_stats(sub, s, None)}
            )
    ex = pd.DataFrame(expl).sort_values("p5_maker", ascending=False)
    ex.to_parquet(OUT / "atlas_cells.parquet")
    lines += [
        md_table(ex.head(15)),
        "",
        f"({len(ex)} gated-in exploratory cells; full table in out/atlas_cells.parquet. "
        "An exploratory cell is promotable only by replicating on CONFIRMATION.)",
        "",
    ]

    report = "\n".join(lines)
    (MODULE / "report" / "atlas_v0.md").write_text(report, encoding="utf-8")
    print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
