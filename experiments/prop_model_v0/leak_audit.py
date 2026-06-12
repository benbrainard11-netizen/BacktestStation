"""LEAK AUDIT — does the champion (NQ-lead) signal survive an honest panel?

Adversarial review (2026-06-14) found the cross-asset block was built from a
UTC-binned daily panel: its "day D" peer close = last bar before 00:00 UTC =
~19:59 ET, which is ~2h INSIDE trading day D+1 — the same session the y_tbR
label races over from its 18:00 ET open. Feature window overlapped the label
window via the most-correlated peers. features_index.py now builds x_* from
TD-convention closes (~17:00 ET, strictly pre-label). This script rebuilds all
four symbols and re-runs the exact champion protocol.

LEAKED-PANEL NUMBERS ON RECORD (champion set, mean per-fold IC): ES era +0.108,
NQ era +0.083, replication RTY +0.019 / YM +0.074, ES drop-NQ delta -0.088,
era decile gross +0.06..+0.19R.

PRE-STATED DECISION RULE: the NQ-lead is REAL only if on the honest panel
(a) ES era IC >= +0.05 AND (b) >=2 of 3 fresh symbols keep era IC > 0.
Anything less: the champion-era signal was the UTC leak -> lead is DEAD.

Run: backend/.venv/Scripts/python.exe experiments/prop_model_v0/leak_audit.py
Artifact: report/leak_audit.md
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

MODULE = Path(__file__).resolve().parent
REPO = MODULE.parents[1]
sys.path.insert(0, str(MODULE))
sys.path.insert(0, str(REPO / "experiments" / "btc_model_v0"))
from features_index import build  # noqa: E402
from model_wf import fold_ic, run_wf  # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:  # noqa: BLE001
    pass

SYMS = ["ES.c.0", "NQ.c.0", "RTY.c.0", "YM.c.0"]
ERA = pd.Timestamp("2024-07-01")
LEAKED = {"ES.c.0": 0.108, "NQ.c.0": 0.083, "RTY.c.0": 0.019, "YM.c.0": 0.074}


def champion_feats(f: pd.DataFrame) -> list[str]:
    return [
        c
        for c in f.columns
        if not c.startswith(("y_", "gx_", "ox_", "xs_"))
        and c not in ("rv20_bps", "c_px")
    ]


def main() -> int:
    lines = ["# Leak audit — champion signal on the honest (TD-convention) panel", ""]
    rows = []
    es_store = {}
    for sym in SYMS:
        f = build(sym)  # rebuild with the fixed cross-asset block
        feats = champion_feats(f)
        y = f["y_tbR"]
        out = {"symbol": sym, "era_ic_leaked": LEAKED[sym]}
        if sym == "ES.c.0":
            pc, fc = run_wf(f[feats], y, shuffle_target=True)
            mc = pc.notna() & y.notna()
            out["control"] = round(fold_ic(pc, y, fc, mc), 3)
        pr, fr_ = run_wf(f[feats], y, shuffle_target=False)
        mr = pr.notna() & y.notna()
        era = mr & (pd.DatetimeIndex(f.index) >= ERA)
        out["ic_full"] = round(fold_ic(pr, y, fr_, mr), 3)
        out["ic_era"] = round(fold_ic(pr, y, fr_, era), 3)
        out["n_era"] = int(era.sum())
        dec = []
        for fid in sorted(fr_[era].unique()):
            m = era & (fr_ == fid)
            if m.sum() < 25:
                continue
            pb = pr[m]
            hi, lo = pb.quantile(0.9), pb.quantile(0.1)
            dec += [y.loc[d] for d, p_ in pb.items() if p_ >= hi]
            dec += [-y.loc[d] for d, p_ in pb.items() if p_ <= lo]
        out["era_decile_grossR"] = round(float(np.mean(dec)), 3) if dec else np.nan
        out["era_decile_n"] = len(dec)
        if sym == "ES.c.0":
            es_store = {"f": f, "feats": feats, "y": y}
        rows.append(out)
        print(out)
    tab = pd.DataFrame(rows)
    lines += [tab.to_string(index=False), ""]

    # drop-NQ attribution on the honest ES model (leaked-panel delta was -0.088)
    f, feats, y = es_store["f"], es_store["feats"], es_store["y"]
    sub = [c for c in feats if not c.startswith("x_nq_")]
    pr, fr_ = run_wf(f[sub], y, shuffle_target=False)
    m = pr.notna() & y.notna() & (pd.DatetimeIndex(f.index) >= ERA)
    ic_nonq = float(spearmanr(pr[m], y[m]).statistic)
    pr2, fr2 = run_wf(f[feats], y, shuffle_target=False)
    m2 = pr2.notna() & y.notna() & (pd.DatetimeIndex(f.index) >= ERA)
    ic_base = float(spearmanr(pr2[m2], y[m2]).statistic)
    lines.append(
        f"ES era pooled IC {ic_base:+.3f} | drop-NQ {ic_nonq:+.3f} "
        f"(delta {ic_nonq - ic_base:+.3f}; leaked-panel delta was -0.088)"
    )
    print(lines[-1])

    fresh = tab[tab["symbol"] != "ES.c.0"]
    es_era = float(tab.loc[tab["symbol"] == "ES.c.0", "ic_era"].iloc[0])
    alive = es_era >= 0.05 and int((fresh["ic_era"] > 0).sum()) >= 2
    lines += [
        "",
        f"pre-stated rule: ES era >= +0.05 AND >=2/3 fresh era > 0",
        f"## VERDICT: {'SIGNAL SURVIVES the leak fix' if alive else 'LEAD IS DEAD — era signal was the UTC panel leak'}",
    ]
    print("\n".join(lines[-2:]))
    (MODULE / "report" / "leak_audit.md").write_text("\n".join(lines), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
