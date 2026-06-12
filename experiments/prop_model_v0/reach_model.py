"""REACH LADDER (Ben's race idea as the TARGET layer) — predict how far tomorrow
travels each way, then use it to place better targets under the champion's signals.

Labels (ES): next-day MFE_up and MFE_dn from the open, in sigma20 units (continuous
reach each direction). Two models (champion features), each judged against the
RV-ONLY baseline (reach ~ vol is trivial; credit only for beating it — the
distance-baseline discipline).

MONETIZATION TEST (the actual point): on the champion's own OOS decile trade days,
re-resolve the bracket on next-day 1m prices under (a) FIXED 1.0σ target / 0.75σ stop
(current rule) vs (b) DYNAMIC target = 0.8 x predicted favorable reach (clipped
0.5σ..2.5σ), same stop. Realized net R head-to-head. If (b) wins, the reach layer
upgrades the strategy with zero new directional alpha.

Run: backend/.venv/Scripts/python.exe experiments/prop_model_v0/reach_model.py
Artifact: report/reach_model.md
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

MODULE = Path(__file__).resolve().parent
REPO = MODULE.parents[1]
sys.path.insert(0, str(MODULE))
sys.path.insert(0, str(REPO / "experiments" / "btc_model_v0"))
from features_index import load_es_minutes  # noqa: E402
from model_wf import fold_ic, run_wf, week_boot_p  # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:  # noqa: BLE001
    pass

COST_PTS = 2.0


def build_reach_labels(f: pd.DataFrame, m: pd.DataFrame):
    mc, mtd = m["c"].to_numpy(float), m["td"].to_numpy()
    days = f.index.to_numpy()
    starts = np.searchsorted(mtd, days)
    up = np.full(len(f), np.nan)
    dn = np.full(len(f), np.nan)
    segs = {}
    rv = f["rv_20"]
    for i in range(len(days) - 2):
        if not np.isfinite(rv.iloc[i]) or rv.iloc[i] <= 0:
            continue
        a, b = starts[i + 1], starts[i + 2]
        seg = mc[a:b]
        if len(seg) < 50:
            continue
        entry = seg[0]
        up[i] = (seg.max() - entry) / (rv.iloc[i] * entry)
        dn[i] = (entry - seg.min()) / (rv.iloc[i] * entry)
        segs[i] = (entry, seg)
    return pd.Series(up, index=f.index), pd.Series(dn, index=f.index), segs


def resolve_bracket(entry, seg, tgt_sig, stp_sig, rv, long: bool):
    tgt = entry * (1 + tgt_sig * rv) if long else entry * (1 - tgt_sig * rv)
    stp = entry * (1 - stp_sig * rv) if long else entry * (1 + stp_sig * rv)
    ht = np.flatnonzero(seg >= tgt) if long else np.flatnonzero(seg <= tgt)
    hs = np.flatnonzero(seg <= stp) if long else np.flatnonzero(seg >= stp)
    it = ht[0] if len(ht) else 10**12
    is_ = hs[0] if len(hs) else 10**12
    risk = stp_sig * rv * entry
    if is_ <= it and is_ < 10**12:
        pnl = -risk
    elif it < 10**12:
        pnl = tgt_sig * rv * entry
    else:
        pnl = (seg[-1] - entry) * (1 if long else -1)
    return (pnl - COST_PTS) / risk


def main() -> int:
    f = pd.read_parquet(MODULE / "data" / "features_es.parquet")
    m = load_es_minutes("ES.c.0")
    y_up, y_dn, segs = build_reach_labels(f, m)
    feats = [
        c
        for c in f.columns
        if not c.startswith(("y_", "gx_", "ox_", "xs_"))
        and c not in ("rv20_bps", "c_px")
    ]
    rv_only = ["rv_5", "rv_10", "rv_20", "rv_60"]

    lines = [
        "# Reach ladder — predict next-day travel; monetize via dynamic targets",
        "",
    ]
    preds = {}
    for nm, yy in [("up", y_up), ("dn", y_dn)]:
        pb, fb = run_wf(f[rv_only], yy, shuffle_target=False)
        pf_, ff_ = run_wf(f[feats], yy, shuffle_target=False)
        mb = pb.notna() & yy.notna()
        mf = pf_.notna() & yy.notna()
        ic_b = fold_ic(pb, yy, fb, mb)
        ic_f = fold_ic(pf_, yy, ff_, mf)
        preds[nm] = pf_
        lines.append(
            f"reach_{nm}: rv-only IC {ic_b:+.3f} | full IC {ic_f:+.3f} | "
            f"value-add {ic_f - ic_b:+.3f}"
        )
        print(lines[-1])

    # monetization: champion direction + reach-based targets
    y_dir = f["y_tbR"]
    pd_, fd_ = run_wf(f[feats], y_dir, shuffle_target=False)
    md = pd_.notna() & y_dir.notna()
    rows = []
    for fid in sorted(fd_[md].unique()):
        mm = md & (fd_ == fid)
        if mm.sum() < 30:
            continue
        pb = pd_[mm]
        hi, lo = pb.quantile(0.9), pb.quantile(0.1)
        for d in pb.index[(pb >= hi) | (pb <= lo)]:
            i = f.index.get_loc(d)
            if i not in segs:
                continue
            entry, seg = segs[i]
            rv = float(f["rv_20"].iloc[i])
            long = pb.loc[d] >= hi
            fav = preds["up"].get(d, np.nan) if long else preds["dn"].get(d, np.nan)
            r_fix = resolve_bracket(entry, seg, 1.0, 0.75, rv, long)
            tgt_dyn = float(np.clip(0.8 * fav, 0.5, 2.5)) if np.isfinite(fav) else 1.0
            r_dyn = resolve_bracket(entry, seg, tgt_dyn, 0.75, rv, long)
            rows.append({"d": d, "fixed": r_fix, "dynamic": r_dyn})
    tr = pd.DataFrame(rows)
    wk = pd.DatetimeIndex(tr["d"]).to_period("W").astype(str).to_numpy()
    for c in ("fixed", "dynamic"):
        net = tr[c].to_numpy(float)
        lines.append(
            f"champion trades n={len(tr)} | {c:7s} exits: mean net R {net.mean():+.3f}, "
            f"week-block p5 {week_boot_p(net, wk, 5):+.3f}"
        )
        print(lines[-1])
    era = pd.DatetimeIndex(tr["d"]) >= pd.Timestamp("2024-07-01")
    lines.append(
        f"era subset (2024-07+, n={int(era.sum())}): fixed {tr.loc[era, 'fixed'].mean():+.3f} "
        f"vs dynamic {tr.loc[era, 'dynamic'].mean():+.3f}"
    )
    print(lines[-1])
    (MODULE / "report" / "reach_model.md").write_text(
        "\n".join(lines), encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
