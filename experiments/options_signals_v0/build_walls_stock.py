"""Per-STOCK dealer-gamma walls from cached EOD option greeks x open_interest (equities).

Stocks can't be band-classified (NVDA~TSLA~MSFT price ranges overlap, and cached files don't record
the root), so this reads ONE ticker by iterating its expirations and calling TS.fetch per expiration
-- the root in the fetch params selects exactly that ticker's hash-keyed cache files. Vendor EOD
greeks carry `gamma` directly (no IV inversion). WINDOW must match the pull's WINDOW so keys hit cache.

Walls = signed net dealer gamma per strike (calls +, puts -), <=30 DTE: argmax=call_wall,
argmin=put_wall, cumsum-crossing=zero_gamma, |net| argmax=pin. Validated vs the stock's EOD close.

Run: THETA_CACHE_ONLY=1 THETA_PORT=25511 python build_walls_stock.py NVDA 2023-01-01 2026-12-31
Artifact: out/walls_<ticker>.parquet  [date, spot, call_wall, put_wall, zero_gamma, pin, gex_proxy]
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import theta_store as TS  # noqa: E402
from gex_pull import _ymd  # noqa: E402

TICKER = sys.argv[1] if len(sys.argv) > 1 else "NVDA"
START = sys.argv[2] if len(sys.argv) > 2 else "2023-01-01"
END = sys.argv[3] if len(sys.argv) > 3 else "2026-12-31"
WINDOW = 35          # must match the pull's WINDOW so TS.fetch keys hit the cache
DTE_MAX = 30
OUT = Path(__file__).resolve().parent / "out" / f"walls_{TICKER.lower()}.parquet"
EOD_BARS = Path(r"D:\data\processed\stocks\eod") / f"{TICKER}.parquet"


def load_chain(start: str, end: str) -> pd.DataFrame:
    s, e = _ymd(start), _ymd(end)
    exps = [x for x in TS.expirations(TICKER) if s <= x <= _ymd(pd.Timestamp(end) + pd.Timedelta(days=90))]
    print(f"{TICKER}: {len(exps)} expirations; reading cached greeks+OI...", flush=True)
    parts = []
    for k, exp in enumerate(exps):
        e_ts = pd.Timestamp(str(exp))
        s_k = max(s, _ymd(e_ts - pd.Timedelta(days=WINDOW)))
        e_k = min(e, exp)
        if s_k > e_k:
            continue
        try:
            gk = TS.fetch("bulk_hist/option/eod_greeks", root=TICKER, exp=exp, start_date=s_k, end_date=e_k)
            oi = TS.fetch("bulk_hist/option/open_interest", root=TICKER, exp=exp, start_date=s_k, end_date=e_k)
        except Exception:
            continue
        if gk.empty or oi.empty:
            continue
        m = gk.merge(oi[["date", "strike", "right", "expiration", "open_interest"]],
                     on=["date", "strike", "right", "expiration"], how="inner")
        if m.empty:
            continue
        parts.append(m[["date", "expiration", "strike", "right", "gamma", "open_interest", "underlying_price"]])
        if k and k % 100 == 0:
            print(f"  ..{k}/{len(exps)}", flush=True)
    if not parts:
        raise RuntimeError(f"no cached {TICKER} option data in range (pull EOD options first)")
    df = pd.concat(parts, ignore_index=True)
    df = df[df["gamma"] > 0].drop_duplicates(subset=["date", "strike", "right", "expiration"])
    df["right"] = df["right"].astype(str).str.upper().str[0]
    print(f"chain rows: {len(df)}", flush=True)
    return df


def _zero_gamma(strikes: np.ndarray, prof: np.ndarray) -> float:
    cum = np.cumsum(prof)
    x = np.where(np.diff(np.sign(cum)) != 0)[0]
    if not len(x):
        return float("nan")
    i = x[0]
    if cum[i] == cum[i + 1]:
        return float(strikes[i])
    return float(np.interp(0, [cum[i], cum[i + 1]], [strikes[i], strikes[i + 1]]))


def main() -> int:
    chain = load_chain(START, END)
    dd = pd.to_datetime(chain["date"].astype(int).astype(str), format="%Y%m%d")
    de = pd.to_datetime(chain["expiration"].astype(int).astype(str), format="%Y%m%d")
    chain = chain[((de - dd).dt.days >= 0) & ((de - dd).dt.days <= DTE_MAX)].copy()
    sign = np.where(chain["right"] == "C", 1.0, -1.0)
    chain["net"] = chain["gamma"].to_numpy(float) * chain["open_interest"].to_numpy(float) * sign

    rows = []
    for D, g in chain.groupby("date"):
        spot = float(g["underlying_price"].median())
        per = g.groupby("strike")["net"].sum().sort_index()
        if len(per) < 5:
            continue
        strikes, prof = per.index.to_numpy(float), per.to_numpy(float)
        aprof = g.groupby("strike")["net"].apply(lambda s: s.abs().sum()).reindex(per.index).to_numpy(float)
        rows.append({"date": int(D), "spot": spot,
                     "call_wall": float(strikes[np.argmax(prof)]),
                     "put_wall": float(strikes[np.argmin(prof)]),
                     "zero_gamma": _zero_gamma(strikes, prof),
                     "pin": float(strikes[np.argmax(aprof)]),
                     "gex_proxy": float((prof * spot * spot * 0.01 * 100).sum())})
    w = pd.DataFrame(rows).sort_values("date").reset_index(drop=True)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    tmp = OUT.with_suffix(".tmp.parquet")
    w.to_parquet(tmp)
    tmp.replace(OUT)
    yrs = pd.Series(pd.to_datetime(w["date"].astype(str), format="%Y%m%d").dt.year).value_counts().sort_index()
    print(f"\nwalls_{TICKER.lower()}: {len(w)} days {int(w['date'].min())}..{int(w['date'].max())}; days/yr {yrs.to_dict()}")

    # validate spot vs the stock's own EOD close
    if EOD_BARS.exists():
        eod = pd.read_parquet(EOD_BARS)[["date", "close"]]
        m = w.merge(eod, on="date", how="left").dropna(subset=["close"])
        r = m["spot"] / m["close"]
        print(f"validate vs {TICKER} EOD close ({len(m)} days): median ratio {r.median():.4f}  within 3%: {(r.sub(1).abs()<0.03).mean():.1%}")
    else:
        print(f"(no EOD bars at {EOD_BARS} yet — skip validation; spot from option underlying_price)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
