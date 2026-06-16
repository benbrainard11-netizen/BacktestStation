"""Bounded vendor probe: does ThetaData actually HAVE pre-2024 RUT/DJX (and pre-2017 SPX)?
Expirations being LISTED != data existing (cf. NDX: expirations listed but eod_greeks=472).
So we sample one mid-year expiration per probe-year and fetch a 7-day eod_greeks window
(and raw eod as a self-compute fallback). rows>0 = vendor has it (=> pullable); empty = no data.

Fast-fail so a no-data answer doesn't hang: THETA_TIMEOUT=25, THETA_RETRIES=1, one Terminal.
"""
from __future__ import annotations

import os

os.environ.setdefault("THETA_TIMEOUT", "25")
os.environ.setdefault("THETA_RETRIES", "1")
os.environ.setdefault("THETA_PORT", "25511")

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import theta_store as TS  # noqa: E402

PROBES = {
    "RUT":  [2018, 2021, 2023],
    "RUTW": [2018, 2021, 2023],
    "DJX":  [2018, 2021, 2023],
    "SPXW": [2014, 2015, 2016],
}


def probe(root: str, yr: int) -> str:
    try:
        exps = sorted(int(x) for x in TS.expirations(root))
    except Exception as e:
        return f"expirations FAIL ({type(e).__name__})"
    cand = [e for e in exps if yr * 10000 <= e < (yr + 1) * 10000]
    if not cand:
        return f"no {yr} expirations listed (exps {exps[0]}..{exps[-1]})"
    exp = min(cand, key=lambda e: abs(e - (yr * 10000 + 630)))
    start = int((pd.Timestamp(str(exp)) - pd.Timedelta(days=7)).strftime("%Y%m%d"))
    out = []
    for ep in ("bulk_hist/option/eod_greeks", "bulk_hist/option/eod"):
        try:
            df = TS.fetch(ep, root=root, exp=exp, start_date=start, end_date=exp)
            out.append(f"{ep.split('/')[-1]}={len(df)}")
        except Exception as e:
            out.append(f"{ep.split('/')[-1]}=ERR({type(e).__name__})")
    return f"exp {exp}: " + "  ".join(out)


for root, years in PROBES.items():
    print(f"\n=== {root} ===", flush=True)
    for yr in years:
        print(f"  {yr}: {probe(root, yr)}", flush=True)
