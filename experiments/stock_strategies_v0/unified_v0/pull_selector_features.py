"""Pull the FREE 'squeeze' features for a dedicated breakout selector: short interest (+days-to-cover)
and short-volume ratio, per ticker, then as-of/window-join them onto the 18k breakout sample (which
already has intraday R). Output out/selector_feats.parquet. Reads env POLYGON_API_KEY.
Run with backend\\.venv\\Scripts\\python.exe.
"""
from __future__ import annotations

import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import numpy as np
import pandas as pd
import requests

KEY = os.environ["POLYGON_API_KEY"]
HOST = "https://api.polygon.io"
HERE = Path(__file__).resolve().parent
CACHE = Path(r"D:\data\processed\stocks\polygon\selector_feats")
(CACHE / "si").mkdir(parents=True, exist_ok=True)
(CACHE / "sv").mkdir(parents=True, exist_ok=True)
_SESS = requests.Session()


def fetch_series(kind, tkr):
    fp = CACHE / kind / f"{tkr}.parquet"
    if fp.exists():
        return
    path = "/stocks/v1/short-interest" if kind == "si" else "/stocks/v1/short-volume"
    for a in range(4):
        try:
            r = _SESS.get(f"{HOST}{path}", params={"ticker": tkr, "limit": 50000, "order": "asc", "apiKey": KEY}, timeout=40)
            if r.status_code == 429:
                time.sleep(1.5 * (a + 1)); continue
            r.raise_for_status()
            res = r.json().get("results") or []
            pd.DataFrame(res).to_parquet(fp)
            return
        except Exception:
            if a == 3:
                pd.DataFrame().to_parquet(fp); return
            time.sleep(1.0 * (a + 1))


def pull_all(tickers):
    jobs = [(k, t) for t in tickers for k in ("si", "sv")]
    print(f"pulling SI+SV for {len(tickers):,} tickers ({len(jobs):,} calls)...")
    done = 0
    with ThreadPoolExecutor(max_workers=12) as ex:
        futs = [ex.submit(fetch_series, k, t) for k, t in jobs]
        for f in as_completed(futs):
            f.result(); done += 1
            if done % 2000 == 0:
                print(f"  {done:,}/{len(jobs):,}")


def to_int(s):
    return pd.to_datetime(s).dt.strftime("%Y%m%d").astype(int)


def build(setups):
    rows = []
    for tkr, g in setups.groupby("ticker"):
        sif = CACHE / "si" / f"{tkr}.parquet"
        svf = CACHE / "sv" / f"{tkr}.parquet"
        si = pd.read_parquet(sif) if sif.exists() else pd.DataFrame()
        sv = pd.read_parquet(svf) if svf.exists() else pd.DataFrame()
        if len(si) and "settlement_date" in si:
            si = si.copy(); si["d"] = to_int(si["settlement_date"]); si = si.sort_values("d")
            si["si_chg"] = si["short_interest"].pct_change()
        if len(sv) and "date" in sv:
            sv = sv.copy(); sv["d"] = to_int(sv["date"]); sv = sv.sort_values("d")
            sv["ratio"] = sv["short_volume"] / sv["total_volume"].replace(0, np.nan)
        for r in g.itertuples(index=False):
            D = int(r.date)
            dtc = si_lvl = si_chg = np.nan
            if len(si):
                past = si[si["d"] <= D]
                if len(past):
                    last = past.iloc[-1]
                    dtc = last.get("days_to_cover", np.nan)
                    si_lvl = last.get("short_interest", np.nan)
                    si_chg = last.get("si_chg", np.nan)
            sv_ratio = np.nan
            if len(sv):
                win = sv[(sv["d"] < D) & (sv["d"] >= D - 100)]   # ~20 trading days back by calendar
                if len(win):
                    sv_ratio = win["ratio"].tail(20).mean()
            rows.append({"tkr": tkr, "date": D, "days_to_cover": dtc, "short_int": si_lvl,
                         "si_chg": si_chg, "short_vol_ratio": sv_ratio})
    F = pd.DataFrame(rows)
    F.to_parquet(HERE / "out" / "selector_feats.parquet")
    cov = F.notna().mean() * 100
    print(f"\nselector_feats: {len(F):,} rows | coverage% "
          f"dtc {cov['days_to_cover']:.0f} short_int {cov['short_int']:.0f} "
          f"si_chg {cov['si_chg']:.0f} short_vol_ratio {cov['short_vol_ratio']:.0f}")
    print(F[["days_to_cover", "short_int", "si_chg", "short_vol_ratio"]].describe().round(3).to_string())


def main():
    res = pd.read_parquet(HERE / "out" / "intraday_entry_results.parquet")[["tkr", "date"]]
    res.columns = ["ticker", "date"]
    pull_all(sorted(res["ticker"].unique()))
    build(res)


if __name__ == "__main__":
    main()
