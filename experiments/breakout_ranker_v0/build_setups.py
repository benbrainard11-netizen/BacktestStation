"""Build the advice's setup table + a matched null-control sample, in one pass over the
survivorship-clean Polygon universe (2016-2026).

GATED SETUP (advice's "clean setup", all causal at day i):
  liquid (close>=$10, 20d $vol>=$30M) AND compressing near the 52-week high:
    - close within 8% of the 252d high, still <= pivot (in the base, not extended)
    - tight base: (pivot-base_low)/close <= 15% over the last 20 sessions
    - volatility contracted: atr14 < atr50
    - uptrend: close>rising-ma50 and close>rising-ma200
  pivot = 20d high; trigger = pivot + 0.10*ATR; stop = base low; +2R/-1R within 20d.

NULL CONTROL: random liquid NON-setup days in the same names, armed+resolved with the
IDENTICAL mechanic (pivot=20d high, same trigger/stop/barrier). If the gated setups don't
beat these, the "compression near highs in a strong sector" selection adds nothing.

Run with backend\\.venv\\Scripts\\python.exe -u.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

import common as C
from barrier import arm_and_resolve

RNG = np.random.default_rng(0)


def _spy_dicts(df):
    spy = df[df["ticker"] == "SPY"].sort_values("date").set_index("date")["close"]
    ma50 = spy.rolling(50).mean()
    return {
        "close": spy.to_dict(),
        "above50": (spy > ma50).to_dict(),
        "ret60": (spy / spy.shift(60) - 1).to_dict(),
        "ret126": (spy / spy.shift(126) - 1).to_dict(),
    }


def _ticker_arrays(d):
    o = d["open"].to_numpy(float)
    h = d["high"].to_numpy(float)
    l = d["low"].to_numpy(float)
    c = d["close"].to_numpy(float)
    v = d["volume"].to_numpy(float)
    s = pd.Series
    return dict(
        o=o, h=h, l=l, c=c, v=v, dts=d["date"].to_numpy().astype(int),
        atr14=C.atr(h, l, c, 14), atr50=C.atr(h, l, c, 50),
        ma50=s(c).rolling(50).mean().to_numpy(), ma200=s(c).rolling(200).mean().to_numpy(),
        pivot=s(h).rolling(C.BASE).max().to_numpy(), base_low=s(l).rolling(C.BASE).min().to_numpy(),
        hi252=s(h).rolling(252).max().to_numpy(),
        dvol=s(c * v).rolling(20).mean().shift(1).to_numpy(),
        clv20=s(np.where(h > l, (c - l) / np.where(h > l, h - l, 1.0), 0.5)).rolling(20).mean().to_numpy(),
    )


def _updnvol(c, v, i):
    ret = c[i - 19:i + 1] - c[i - 20:i]
    vv = v[i - 19:i + 1]
    up, dn = vv[ret > 0].sum(), vv[ret < 0].sum()
    return up / dn if dn > 0 else np.nan


def _is_setup(a, i):
    """The advice gate at day i (all data <= i)."""
    c, piv, lo = a["c"][i], a["pivot"][i], a["base_low"][i]
    if not np.isfinite(piv) or not np.isfinite(a["ma200"][i]) or not np.isfinite(a["hi252"][i]):
        return False
    if c < C.MIN_PRICE or not np.isfinite(a["dvol"][i]) or a["dvol"][i] < C.MIN_DVOL:
        return False
    if c / a["hi252"][i] < C.HIGH52_PROX or c > piv * C.NOT_EXTENDED:
        return False
    if (piv - lo) / c > C.MAX_BASE_WIDTH:
        return False
    if not (a["atr50"][i] > 0 and a["atr14"][i] / a["atr50"][i] <= C.MAX_VOL_CONTRACT):
        return False
    if not (c > a["ma50"][i] > a["ma50"][i - 10] and c > a["ma200"][i] > a["ma200"][i - 20]):
        return False
    return True


def _features(a, i, sector, sec_pct, spy):
    c = a["c"][i]
    di = int(a["dts"][i])
    return {
        "regime_up": int(bool(spy["above50"].get(di))),
        "spy_ret60": spy["ret60"].get(di) or 0.0,
        "sector_pct": sec_pct if sec_pct is not None else np.nan,
        "rs_6m": (c / a["c"][i - 126] - 1) - (spy["ret126"].get(di) or 0.0),
        "ret_3m": c / a["c"][i - 63] - 1,
        "ret_6m": c / a["c"][i - 126] - 1,
        "ret_12_1": a["c"][i - 21] / a["c"][i - 252] - 1,
        "high52_prox": c / a["hi252"][i],
        "atr_pct": a["atr14"][i] / c,
        "vol_contract": a["atr14"][i] / a["atr50"][i],
        "base_width": (a["pivot"][i] - a["base_low"][i]) / c,
        "dist_ma50": c / a["ma50"][i] - 1,
        "clv20": a["clv20"][i],
        "updnvol": _updnvol(a["c"], a["v"], i),
        "log_price": np.log(c),
        "log_dvol": np.log(a["dvol"][i] + 1),
    }


def main():
    df = C.load_universe()
    spy = _spy_dicts(df)
    tsec = C.ticker_sector_map()
    print("sector-strength table...", flush=True)
    sec_str = C.sector_strength_table(df, tsec)
    active = df.groupby("ticker")["active"].first().to_dict()

    setup_rows, null_rows = [], []
    nt = 0
    for t, d in df.groupby("ticker", sort=False):
        if t == "SPY" or len(d) < 280:
            continue
        a = _ticker_arrays(d)
        sector = tsec.get(t, "Unknown")
        n = len(a["c"])
        lo_i, hi_i = 252, n - (C.TRIG_WIN + C.BARRIER_DAYS + 1)
        if hi_i <= lo_i:
            continue
        liquid = np.zeros(n, bool)
        setup = np.zeros(n, bool)
        for i in range(lo_i, hi_i):
            if a["c"][i] >= C.MIN_PRICE and np.isfinite(a["dvol"][i]) and a["dvol"][i] >= C.MIN_DVOL:
                liquid[i] = True
                setup[i] = _is_setup(a, i)
        # gated setups
        for i in np.where(setup)[0]:
            r = arm_and_resolve(a["o"], a["h"], a["l"], a["c"], i, a["pivot"][i], a["atr14"][i])
            if r is None:
                continue
            di = int(a["dts"][i])
            row = {"ticker": t, "date": di, "yr": di // 10000, "active": bool(active.get(t, False)),
                   "sector": sector, **_features(a, i, sector, sec_str.get((di, sector)), spy), **r}
            setup_rows.append(row)
        # matched random non-setup liquid days (same mechanic) for the null
        elig = np.where(liquid & ~setup)[0]
        k = int(setup.sum())
        if k and len(elig):
            for j in RNG.choice(elig, size=min(k, len(elig)), replace=False):
                r = arm_and_resolve(a["o"], a["h"], a["l"], a["c"], j, a["pivot"][j], a["atr14"][j])
                if r is None:
                    continue
                dj = int(a["dts"][j])
                null_rows.append({"ticker": t, "date": dj, "yr": dj // 10000, **r})
        nt += 1
        if nt % 1000 == 0:
            print(f"  {nt} tickers | setups {len(setup_rows):,} | null {len(null_rows):,}", flush=True)

    S = pd.DataFrame(setup_rows)
    N = pd.DataFrame(null_rows)
    S.to_parquet(C.OUT / "setups.parquet")
    N.to_parquet(C.OUT / "null.parquet")
    st = S[S["triggered"] == 1]
    nl = N[N["triggered"] == 1]
    print(f"\nGATED setups: detected {len(S):,} | triggered {len(st):,} "
          f"({len(st)/max(len(S),1):.0%}) | tickers {S['ticker'].nunique():,} | "
          f"{S['date'].min()}..{S['date'].max()} | active {int(S['active'].sum()):,}/{int((~S['active']).sum()):,}")
    print(f"NULL triggered: {len(nl):,}")
    print(f"\n=== DECISIVE NULL CONTROL (triggered, +2R/-1R, net of {C.FRIC*1e4:.0f}bps) ===")
    print(f"  GATED setup   win {st['win'].mean():.1%}  meanR {st['netR'].mean():+.3f}  n {len(st):,}")
    print(f"  NULL  random  win {nl['win'].mean():.1%}  meanR {nl['netR'].mean():+.3f}  n {len(nl):,}")
    print(f"  DELTA win {st['win'].mean()-nl['win'].mean():+.1%}  meanR {st['netR'].mean()-nl['netR'].mean():+.3f}")
    print("  READ: delta>0 across years => selection adds edge; delta~0/neg => construction is dead.")


if __name__ == "__main__":
    main()
