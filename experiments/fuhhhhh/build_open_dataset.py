"""Opening-drive dataset: one decision/day at 09:45 ET (after the 15-min opening range).

A 'causal moment' model — predict the direction of the rest-of-day move from overnight +
opening-range context. Bars-only features now; gamma-regime / 0DTE-flow options features
merge in by date later (the real conditioner). Target = 09:45 -> EOD move (continuous +
a +-0.5*ATR run-to-EOD bracket R for long and short).

Causal: every feature uses data <= 09:45; ATR from days < D; entry = 09:45 NQ open.
Covers 2018-2026-03 (holdout 2026-04+ excluded). Simple feature set on purpose (~2000
samples = 1/day; keep the hypothesis small).

Run: backend\\.venv\\Scripts\\python.exe experiments\\fuhhhhh\\build_open_dataset.py
Output: out/open_dataset.parquet
"""
from __future__ import annotations

import sys
from datetime import date as Date
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common as C
import data_io as D
import objectives_labels as OL

OUTDIR = Path(__file__).resolve().parent / "out"
OPEN_MS = 9 * 3600_000 + 30 * 60_000
DEC_MS = 9 * 3600_000 + 45 * 60_000          # decision after 15-min opening range
EOD_MS = 16 * 3600_000
MOVE_ATR = 0.5                               # bracket = +-0.5*ATR, run to EOD


def rth(root, day):
    df = D.load_bars_sym(root, day)
    if df is None:
        return None
    lo, hi = D.et_ts(day, OPEN_MS), D.et_ts(day, EOD_MS)
    out = df[(df["et"] >= lo) & (df["et"] < hi)]
    return out if len(out) else None


def at_or_before(df, t):
    s = df[df["et"] <= t]
    return s if len(s) else None


def main() -> int:
    days = sorted(p.name.split("=")[1] for p in C.BARS_1M_NQ.glob("date=*"))
    days = [d for d in days if "2018-01-01" <= d <= "2026-03-31"]
    atr_tr, rows, prev = D.AtrTracker(), [], None
    print(f"building opening-drive dataset over {len(days)} candidate days")
    for dstr in days:
        day = Date.fromisoformat(dstr)
        nq = rth(C.BARS_1M_NQ, day)
        if nq is None or prev is None:
            atr_tr.push_day(nq) if nq is not None else None
            prev = (day, nq) if nq is not None else prev
            continue
        atr = atr_tr.atr()
        es = rth(C.BARS_1M, day)
        pday, pnq = prev
        t_open, t_dec = D.et_ts(day, OPEN_MS), D.et_ts(day, DEC_MS)
        o930 = nq[nq["et"] >= t_open]
        decbar = nq[nq["et"] >= t_dec]
        orbars = nq[(nq["et"] >= t_open) & (nq["et"] < t_dec)]
        if atr and len(o930) and len(decbar) and len(orbars) >= 5 and pnq is not None:
            open0930 = float(o930["open"].iloc[0])
            entry = float(decbar["open"].iloc[0])              # 09:45 entry
            pclose = float(pnq["close"].iloc[-1])
            pdh, pdl = float(pnq["high"].max()), float(pnq["low"].min())
            orh, orl = float(orbars["high"].max()), float(orbars["low"].min())
            f = {"date": dstr, "yr": dstr[:4], "dow": float(day.weekday()), "atr": atr,
                 "gap_atr": (open0930 - pclose) / atr,
                 "or_drive_atr": (entry - open0930) / atr,
                 "or_range_atr": (orh - orl) / atr,
                 "open_loc": (open0930 - pdl) / (pdh - pdl) if pdh > pdl else 0.5,
                 "prev_ret_atr": (pclose - float(pnq["open"].iloc[0])) / atr,
                 "entry": entry}
            if es is not None:
                e930 = es[es["et"] >= t_open]; edec = es[es["et"] >= t_dec]
                pes = rth(C.BARS_1M, pday)
                if len(e930) and len(edec) and pes is not None:
                    eopen, eentry, epc = float(e930["open"].iloc[0]), float(edec["open"].iloc[0]), float(pes["close"].iloc[-1])
                    eatr = max(epc * 0.004, 1.0)               # rough ES atr proxy for normalization
                    f["es_gap"] = (eopen - epc) / epc
                    f["es_or_drive"] = (eentry - eopen) / eopen
            # target: 09:45 -> EOD
            fwd = nq[nq["et"] >= t_dec]
            close_eod = float(fwd["close"].iloc[-1])
            f["fwd_eod_atr"] = (close_eod - entry) / atr
            f["y_up"] = int(close_eod > entry)
            move = MOVE_ATR * atr
            yL, ceL, _ = OL.race_label(fwd, entry + move, entry - move)
            rL, rS = OL.realized_r(yL, entry, entry + move, entry - move, ceL, C.COST_PTS_NQ) if yL is not None else (np.nan, np.nan)
            f["r_long"], f["r_short"] = rL, rS
            rows.append(f)
        atr_tr.push_day(nq)
        prev = (day, nq)

    df = pd.DataFrame(rows)
    assert df["date"].max() <= "2026-03-31", "holdout leak"
    df.to_parquet(OUTDIR / "open_dataset.parquet")
    print(f"\n{len(df)} days {df.date.min()}..{df.date.max()}  up-rate={df.y_up.mean():.3f}")
    print("feature cols:", [c for c in df.columns if c not in ("date", "yr", "entry", "y_up", "r_long", "r_short", "fwd_eod_atr")])
    print(df[["gap_atr", "or_drive_atr", "or_range_atr", "open_loc", "fwd_eod_atr"]].describe().round(3).to_string())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
