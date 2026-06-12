"""Rebuild SPX gamma walls 2019->2026 from the RAW caches (cache-only, no Terminal).

Join: eod_greeks (gamma per contract-day, SPX-classified by underlying_price band)
x open_interest (OI per contract-day) on (date, strike, right, expiration).
Per day: strike-level GEX ~ sum(gamma x OI); call_wall = max-GEX call strike,
put_wall = max-GEX put strike, total proxy + spot. VALIDATION: overlap days must
agree with the official gex_levels_spx walls (derived by the audited pipeline).

Run: backend/.venv/Scripts/python.exe experiments/prop_model_v0/build_walls_deep.py
Artifact: data/walls_deep.parquet
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

MODULE = Path(__file__).resolve().parent
REPO = MODULE.parents[1]
GREEKS = Path("D:/data/raw/thetadata/bulk_hist_option_eod_greeks")
OI = Path("D:/data/raw/thetadata/bulk_hist_option_open_interest")

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:  # noqa: BLE001
    pass


def scan(cache: Path, cols: list[str], spx_filter: bool) -> pd.DataFrame:
    files = sorted(cache.glob("*.parquet"))
    print(f"scanning {len(files)} files in {cache.name}")
    parts = []
    for i, fp in enumerate(files):
        try:
            d = pd.read_parquet(fp, columns=cols)
        except Exception:  # noqa: BLE001
            continue
        if d.empty:
            continue
        if spx_filter:
            u = d["underlying_price"].median()
            if not (3000 <= u <= 8500):
                continue
        parts.append(d)
        if (i + 1) % 400 == 0:
            print(f"  ..{i + 1}/{len(files)}")
    return pd.concat(parts, ignore_index=True)


def main() -> int:
    gk = scan(
        GREEKS,
        ["date", "strike", "right", "expiration", "gamma", "underlying_price"],
        spx_filter=True,
    )
    gk = gk[gk["gamma"] > 0].drop_duplicates(
        subset=["date", "strike", "right", "expiration"]
    )
    print(f"greeks rows (SPX, gamma>0): {len(gk)}")
    oi = scan(
        OI, ["date", "strike", "right", "expiration", "open_interest"], spx_filter=False
    )
    oi = oi[oi["open_interest"] > 0].drop_duplicates(
        subset=["date", "strike", "right", "expiration"]
    )
    print(f"OI rows: {len(oi)}")
    j = gk.merge(oi, on=["date", "strike", "right", "expiration"], how="inner")
    print(f"joined contract-days: {len(j)}")
    if j.empty:
        raise RuntimeError("join produced 0 rows — check key alignment")
    j["gexw"] = j["gamma"] * j["open_interest"]
    rows = []
    for dt_, g in j.groupby("date"):
        spot = float(g["underlying_price"].median())
        rt = g["right"].astype(str).str.upper().str[0]
        per = g.groupby([g["strike"], rt])["gexw"].sum().reset_index()
        calls = per[per["right"] == "C"]
        puts = per[per["right"] == "P"]
        if calls.empty or puts.empty:
            continue
        rows.append(
            {
                "date": int(dt_),
                "spot": spot,
                "call_wall": float(calls.loc[calls["gexw"].idxmax(), "strike"]),
                "put_wall": float(puts.loc[puts["gexw"].idxmax(), "strike"]),
                "gex_proxy": float(calls["gexw"].sum() - puts["gexw"].sum()),
            }
        )
    w = pd.DataFrame(rows).sort_values("date").reset_index(drop=True)
    # validation vs the official derived walls on overlap
    off = pd.read_parquet(
        REPO / "experiments" / "options_signals_v0" / "out" / "gex_levels_spx.parquet"
    )
    mrg = w.merge(off, on="date", suffixes=("_deep", "_off"))
    if len(mrg):
        cw_diff = (mrg["call_wall_deep"] - mrg["call_wall_off"]).abs() / mrg["spot_off"]
        pw_diff = (mrg["put_wall_deep"] - mrg["put_wall_off"]).abs() / mrg["spot_off"]
        print(
            f"validation vs official ({len(mrg)} overlap days): "
            f"call wall median |diff| {cw_diff.median():.3%}, put {pw_diff.median():.3%}; "
            f"exact-strike match: call {(cw_diff == 0).mean():.0%}, put {(pw_diff == 0).mean():.0%}"
        )
    (MODULE / "data").mkdir(exist_ok=True)
    w.to_parquet(MODULE / "data" / "walls_deep.parquet")
    print(f"walls: {len(w)} days ({w['date'].min()} -> {w['date'].max()})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
