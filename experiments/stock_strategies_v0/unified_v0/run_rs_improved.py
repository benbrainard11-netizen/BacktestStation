"""Relative-strength book, IMPROVED per the grounded research plan: vol-managed + residual
(beta-neutral) momentum + inverse-vol weights + concentration cap + rank-buffer turnover +
partial beta-hedge, with cost sweep and proper benchmarks (RSP/IWM/QQQ/MTUM, not just SPY).
One consistent backtest engine, one data load. Clean Polygon (delisted captured honestly).
Run with backend\\.venv\\Scripts\\python.exe.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

POLY = Path(r"D:\data\processed\stocks\polygon")
MIN_PRICE, MIN_DVOL = 5.0, 5e6


# ---------- data ----------
def load():
    df = pd.concat([pd.read_parquet(f) for f in sorted(POLY.glob("daily_*.parquet"))], ignore_index=True)
    df["dt"] = pd.to_datetime(df["date"].astype(int).astype(str), format="%Y%m%d")
    df["dvol"] = df["close"] * df["volume"]
    cs = set(pd.read_parquet(POLY / "meta.parquet")["ticker"])
    bench = {b: df[df["ticker"] == b].set_index("dt")["close"].resample("ME").last()
             for b in ("SPY", "RSP", "IWM", "QQQ", "MTUM")}
    cd = df[df["ticker"].isin(cs)].pivot_table(index="dt", columns="ticker", values="close")
    me = df[df["ticker"].isin(cs)].groupby("ticker").resample("ME", on="dt").agg(
        close=("close", "last"), dvol=("dvol", "mean"))
    close_m = me["close"].unstack(0)
    dvol_m = me["dvol"].unstack(0)
    return cd, close_m, dvol_m, bench


# ---------- weights ----------
def cap_weights(w: pd.Series, cap: float) -> pd.Series:
    w = w / w.sum()
    for _ in range(20):
        over = w > cap
        if not over.any():
            break
        excess = (w[over] - cap).sum()
        w[over] = cap
        und = w < cap
        if not und.any():
            break
        w[und] += excess * (w[und] / w[und].sum())
    return w


def metrics(rets: pd.Series, label, bench=None):
    rets = rets.dropna()
    if len(rets) < 12:
        print(f"  {label}: too few"); return None
    eq = (1 + rets).cumprod()
    cagr = eq.iloc[-1] ** (12 / len(rets)) - 1
    vol = rets.std() * np.sqrt(12)
    sharpe = rets.mean() / rets.std() * np.sqrt(12) if rets.std() else 0
    dd = (eq / eq.cummax() - 1).min()
    calmar = cagr / abs(dd) if dd else 0
    ex = ""
    if bench is not None:
        b = bench.reindex(rets.index)
        ex = f"  alpha {(rets - b).mean()*12*100:+5.1f}%"
    print(f"  {label:34s} CAGR {cagr*100:+6.1f}%  vol {vol*100:3.0f}%  Sharpe {sharpe:+.2f}  "
          f"maxDD {dd*100:4.0f}%  Calmar {calmar:+.2f}{ex}")
    return dict(cagr=cagr, sharpe=sharpe, calmar=calmar, dd=dd)


def main():
    cd, close_m, dvol_m, bench = load()
    print(f"universe {close_m.shape[1]:,} x {close_m.shape[0]} months "
          f"({close_m.index[0].date()}..{close_m.index[-1].date()})")
    Rd = cd.pct_change()
    spy_d = bench["SPY"]                                  # SPY monthly close

    # SPY daily returns aligned to Rd index (SPY is an ETF, not in the common-stock panel -> reload)
    dfa = pd.concat([pd.read_parquet(f) for f in sorted(POLY.glob("daily_*.parquet"))], ignore_index=True)
    dfa["dt"] = pd.to_datetime(dfa["date"].astype(int).astype(str), format="%Y%m%d")
    spy_daily_ret = dfa[dfa["ticker"] == "SPY"].set_index("dt")["close"].reindex(cd.index).pct_change()

    me_idx = close_m.index
    pos = cd.index.get_indexer(me_idx, method="ffill")
    cols = cd.columns

    raw = (close_m.shift(1) / close_m.shift(12) - 1)
    fwd = close_m.shift(-1) / close_m - 1
    liq = (close_m >= MIN_PRICE) & (dvol_m >= MIN_DVOL)
    spy_fwd = (spy_d.shift(-1) / spy_d - 1).reindex(me_idx)

    vol63 = pd.DataFrame(index=me_idx, columns=cols, dtype=float)
    beta = pd.DataFrame(index=me_idx, columns=cols, dtype=float)
    rmom = pd.DataFrame(index=me_idx, columns=cols, dtype=float)
    rvol = pd.DataFrame(index=me_idx, columns=cols, dtype=float)
    Rn = Rd.to_numpy(); spn = spy_daily_ret.to_numpy()
    for k, p in enumerate(pos):
        if p < 252:
            continue
        w = Rn[p - 252:p - 21]; s = spn[p - 252:p - 21]
        m = ~np.isnan(s)
        w, s = w[m], s[m]
        cnt = (~np.isnan(w)).sum(0)
        good = cnt >= 180
        meanR = np.nanmean(w, 0); meanS = s.mean()
        cov = np.nanmean(w * s[:, None], 0) - meanR * meanS
        b = cov / (s.var() + 1e-12)
        resid = w - b[None, :] * s[:, None]
        rmom.iloc[k] = np.where(good, np.nansum(resid, 0), np.nan)
        rvol.iloc[k] = np.where(good, np.nanstd(resid, 0) * np.sqrt(252), np.nan)
        beta.iloc[k] = np.where(good, b, np.nan)
        v = Rn[p - 63:p]
        vol63.iloc[k] = np.nanstd(v, 0) * np.sqrt(252)

    def run(score, weight="ew", n=None, decile=True, cap=0.03, buffer=None,
            vol_target=None, beta_target=None, cost=0.001):
        held = pd.Series(dtype=float); rets = []; idx = []; turn = []; hold_rec = []
        for k, t in enumerate(me_idx):
            sc, fr, lq = score.loc[t], fwd.loc[t], liq.loc[t]
            ok = sc.notna() & fr.notna() & lq & vol63.loc[t].notna()
            if ok.sum() < 20:
                continue
            ranked = sc[ok].sort_values(ascending=False); N = len(ranked)
            tn = max(10, int(N * 0.1)) if decile else min(n, N)
            if buffer:
                en = max(10, int(N * buffer[0])); ex = int(N * buffer[1])
                rank_of = {nm: i for i, nm in enumerate(ranked.index)}
                keep = [nm for nm in held.index if rank_of.get(nm, 1e9) < ex]
                adds = [nm for nm in ranked.index[:en] if nm not in keep][:max(0, tn - len(keep))]
                names = keep + adds
            else:
                names = list(ranked.index[:tn])
            iv = 1.0 / vol63.loc[t, names] if weight == "invvol" else pd.Series(1.0, index=names)
            w = cap_weights(iv.replace([np.inf, np.nan], iv.median()), cap)
            gross = 1.0
            if vol_target:
                p = pos[k]; win = Rn[p - 63:p][:, [cd.columns.get_loc(x) for x in names]]
                pr = np.nansum(win * w.values[None, :], 1); bv = np.nanstd(pr) * np.sqrt(252)
                gross = float(np.clip(vol_target / bv, 0.35, 1.0)) if bv > 0 else 1.0
            wg = w * gross
            r = float((wg * fr.reindex(wg.index)).sum())
            if beta_target is not None:
                pb = float((wg * beta.loc[t].reindex(wg.index)).sum())
                h = pb - beta_target
                r -= h * (spy_fwd.loc[t] if not pd.isna(spy_fwd.loc[t]) else 0) + abs(h) * 0.0001
            alln = set(wg.index) | set(held.index)
            to = sum(abs(wg.get(n, 0) - held.get(n, 0)) for n in alln)
            rets.append(r - to * cost); turn.append(to); idx.append(t); held = wg
            for nm, wv in wg.items():
                hold_rec.append((t, nm, float(wv)))
        s = pd.Series(rets, index=pd.DatetimeIndex(idx)); s.attrs["turn"] = np.mean(turn) * 12
        s.attrs["holdings"] = hold_rec
        return s

    scores = {"raw": raw, "raw/vol": raw / vol63, "residual": rmom, "residual/rvol": rmom / rvol}
    spy_ret_m = (spy_d / spy_d.shift(1) - 1)

    print("\n=== EXP1+2: the 4-book matrix (top decile, cap 3%, monthly, 10bps) ===")
    best, best_s, best_name = None, None, None
    for nm, sc in scores.items():
        wt = "invvol" if "vol" in nm else "ew"
        s = run(sc, weight=wt)
        m = metrics(s, f"{nm} ({wt})  [turn {s.attrs['turn']*100:.0f}%]", bench=spy_ret_m)
        if m and (best is None or m["sharpe"] > best["sharpe"]):
            best, best_s, best_name = m, s, nm
    print(f"  -> best book by Sharpe: {best_name}")
    bw = "invvol" if "vol" in best_name else "ew"

    print("\n=== EXP1C: + portfolio vol-target (16%, no leverage) ===")
    metrics(run(scores[best_name], weight=bw, vol_target=0.16), f"{best_name} + voltgt16", bench=spy_ret_m)

    print("\n=== EXP3: + beta-target hedge sweep (best book + vol-target) ===")
    for bt in (1.0, 0.75, 0.50, 0.25, 0.0):
        metrics(run(scores[best_name], weight=bw, vol_target=0.16, beta_target=bt),
                f"{best_name} voltgt + beta={bt:.2f}", bench=spy_ret_m)

    print("\n=== EXP4: + rank-buffer turnover (best book + vol-target, beta 0.5) ===")
    for ex in (0.20, 0.30, 0.40):
        s = run(scores[best_name], weight=bw, vol_target=0.16, beta_target=0.5, buffer=(0.10, ex))
        metrics(s, f"{best_name} buffer enter10/exit{int(ex*100)}  [turn {s.attrs['turn']*100:.0f}%]", bench=spy_ret_m)

    print("\n=== EXP-cost: cost sweep on best book + vol-target + beta0.5 + buffer30 ===")
    for c in (0.001, 0.0025, 0.005, 0.010):
        s = run(scores[best_name], weight=bw, vol_target=0.16, beta_target=0.5, buffer=(0.10, 0.30), cost=c)
        metrics(s, f"cost {c*1e4:.0f}bps/side", bench=spy_ret_m)

    print("\n=== DEPLOYABLE: residual/rvol + invvol + cap3% + buffer(10/40) + NO hedge ===")
    dep = run(scores["residual/rvol"], weight="invvol", cap=0.03, buffer=(0.10, 0.40))
    for c in (0.001, 0.0025, 0.005):
        s = run(scores["residual/rvol"], weight="invvol", cap=0.03, buffer=(0.10, 0.40), cost=c)
        metrics(s, f"deployable cost {c*1e4:.0f}bps  [turn {s.attrs['turn']*100:.0f}%]", bench=spy_ret_m)
    print("  -- lumpiness check --")
    metrics(dep[dep.index.year < 2026], "deployable EX-2026 (drop the hot partial yr)", bench=spy_ret_m)
    metrics(dep[dep.index.year >= 2024], "deployable 2024+ (recent)", bench=spy_ret_m)
    print("  -- by year (deployable vs SPY) --")
    for y in range(dep.index[0].year, dep.index[-1].year + 1):
        a = (1 + dep[dep.index.year == y]).prod() - 1
        b = (1 + spy_ret_m.reindex(dep.index)[dep.index.year == y]).prod() - 1
        print(f"    {y}: book {a*100:+6.1f}%   SPY {b*100:+6.1f}%   excess {(a-b)*100:+5.1f}%")

    print("\n=== benchmark diagnostics, MATCHED to the deployable book's months ===")
    for b, px in bench.items():
        metrics((px / px.shift(1) - 1).reindex(dep.index), f"{b} buy&hold")

    # --- save verification artifacts ---
    ART = Path(__file__).resolve().parent / "out" / "rs_artifacts"; ART.mkdir(parents=True, exist_ok=True)
    hr = pd.DataFrame(dep.attrs["holdings"], columns=["date", "ticker", "weight"])
    hr.to_parquet(ART / "holdings.parquet")
    dep.attrs = {}                                   # drop non-serializable holdings before saving
    dep.to_frame("ret").to_parquet(ART / "returns.parquet")
    for nm, p in [("rmom", rmom), ("rvol", rvol), ("beta", beta), ("vol63", vol63),
                  ("raw", raw), ("fwd", fwd), ("liq", liq), ("close_m", close_m), ("dvol_m", dvol_m)]:
        p.to_parquet(ART / f"{nm}.parquet")
    spy_daily_ret.to_frame("spy_ret").to_parquet(ART / "spy_daily_ret.parquet")
    held = set(hr["ticker"]) | {"SPY", "QQQ", "RSP", "IWM", "MTUM"}
    dfa[dfa["ticker"].isin(held)][["ticker", "date", "open", "high", "low", "close", "volume"]] \
        .to_parquet(ART / "daily_slim2.parquet")
    print(f"\nsaved verification artifacts to {ART} ({hr['ticker'].nunique()} names ever held)")


if __name__ == "__main__":
    main()
