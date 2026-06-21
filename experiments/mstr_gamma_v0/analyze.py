"""analyze — MSTR dealer-gamma -> MSTR direction / vol, leak-checked, design/holdout.

H1 (regime-conditional direction): GEX_t<0 (dealers short gamma) -> momentum (follow r_t);
   GEX_t>0 (long gamma/pin) -> fade (revert). Does the regime SPLIT beat always-momentum / always-fade?
H1b: above/below zero_gamma -> next-day direction.
H3 (gamma -> vol): does GEX magnitude (spot^2-normalized) predict next-day realized vol?

All features known at close t (gex_proxy/walls from EOD greeks + that-day OI); outcome = day t+1.
Split-safe: returns from Polygon ADJUSTED close; GEX sign is split-invariant; magnitude /spot^2;
wall distances are ratios. Design <= 2025-09-30; holdout 2025-10-01 -> 2026-06-30 (read once).

  python analyze.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from data_io import load_polygon_daily  # noqa: E402

WALLS = ROOT / "experiments" / "options_signals_v0" / "out" / "walls_mstr.parquet"
DESIGN_END = 20250930


def load():
    w = pd.read_parquet(WALLS).sort_values("date").reset_index(drop=True)
    px = load_polygon_daily("MSTR").drop_duplicates("date").sort_values("date")
    px = px[["date", "open", "high", "low", "close"]].rename(columns={"open": "adj_open",
            "high": "adj_high", "low": "adj_low", "close": "adj_close"})
    df = w.merge(px, on="date", how="inner")
    df["r"] = df["adj_close"].pct_change()              # split-safe adjusted daily return
    # split factor (adjusted/contract) to place contract-space walls onto adjusted OHLC
    df["fac"] = df["adj_close"] / df["spot"]
    for c in ["call_wall", "put_wall", "zero_gamma", "pin"]:
        df[c + "_adj"] = df[c] * df["fac"]
    # prior-day walls (causal: known at close t, used for day t+1)
    for c in ["call_wall_adj", "put_wall_adj", "pin_adj"]:
        df[c + "_p"] = df[c].shift(1)
    df["r_fwd"] = df["r"].shift(-1)                     # next-day return (outcome)
    df["absr_fwd"] = df["r_fwd"].abs()
    # causal features at close t
    df["gex_sign"] = np.sign(df["gex_proxy"])
    df["gex_norm"] = df["gex_proxy"] / (df["spot"] ** 2)   # remove spot^2 scaling (split-safe magnitude)
    df["above_zg"] = (df["spot"] > df["zero_gamma"]).astype(float)
    df["dist_call"] = (df["call_wall"] - df["spot"]) / df["spot"]
    df["dist_put"] = (df["spot"] - df["put_wall"]) / df["spot"]
    return df.dropna(subset=["r", "r_fwd", "gex_proxy"]).reset_index(drop=True)


def summ(x):
    x = np.asarray(x, float)
    if len(x) < 10:
        return None
    k = max(1, int(np.ceil(0.05 * len(x))))
    return dict(n=len(x), mean=x.mean(), med=float(np.median(x)), win=(x > 0).mean(),
                ex_top5=np.sort(x)[:len(x) - k].mean(),
                sharpe=x.mean() / (x.std() + 1e-12) * np.sqrt(252))


def h1(d, label):
    # regime-conditional directional strategy (next-day), leak-safe
    neg = d["gex_sign"] < 0
    pos = d["gex_sign"] > 0
    pos_mom = np.sign(d["r"]) * d["r_fwd"]            # always momentum
    pos_rev = -np.sign(d["r"]) * d["r_fwd"]           # always fade
    cond = np.where(neg, np.sign(d["r"]), -np.sign(d["r"])) * d["r_fwd"]  # neg->mom, pos->fade
    print(f"  [{label}] n={len(d)} negGEX={neg.mean():.2f}")
    for nm, s in [("always_momentum", summ(pos_mom)), ("always_fade", summ(pos_rev)),
                  ("regime_conditional", summ(cond))]:
        if s:
            print(f"    {nm:20s} mean_r_fwd={s['mean']:+.4f} sharpe={s['sharpe']:+.2f} "
                  f"win={s['win']:.3f} ex-top5%={s['ex_top5']:+.4f}")
    # autocorr by regime (diagnostic): does neg-GEX -> momentum (corr r,r_fwd >0)?
    for nm, mask in [("negGEX(trend?)", neg), ("posGEX(revert?)", pos)]:
        sub = d[mask]
        if len(sub) > 20:
            c = np.corrcoef(sub["r"], sub["r_fwd"])[0, 1]
            print(f"    autocorr corr(r_t,r_t+1) | {nm:16s} = {c:+.3f}")


def h3(d, label):
    # gamma magnitude -> next-day realized vol (|r_fwd|)
    ic_norm = np.corrcoef(d["gex_norm"], d["absr_fwd"])[0, 1]
    ic_sign = np.corrcoef(d["gex_sign"], d["absr_fwd"])[0, 1]
    # above zero-gamma -> direction
    ic_zg = np.corrcoef(d["above_zg"], d["r_fwd"])[0, 1]
    print(f"  [{label}] gex_norm->|r_fwd| IC={ic_norm:+.3f} | gex_sign->|r_fwd| IC={ic_sign:+.3f} "
          f"| above_zg->r_fwd IC={ic_zg:+.3f}")


def h2(d, label):
    """Coarse daily wall reaction using prior-day walls on adjusted OHLC (causal).
    pin gravitation: did close move toward prior pin from the open? wall reject: touch the wall then
    close back inside? containment: open inside [put,call] -> stays?"""
    d = d.dropna(subset=["pin_adj_p", "call_wall_adj_p", "put_wall_adj_p"]).copy()
    # pin gravitation (vs 0.5 null)
    grav = (d.adj_close.sub(d.pin_adj_p).abs() < d.adj_open.sub(d.pin_adj_p).abs()).mean()
    # call-wall rejection: high pierced prior call_wall -> closed back below?
    pierce_c = d[d.adj_high >= d.call_wall_adj_p]
    rej_c = (pierce_c.adj_close < pierce_c.call_wall_adj_p).mean() if len(pierce_c) > 10 else np.nan
    # put-wall bounce: low pierced prior put_wall -> closed back above?
    pierce_p = d[d.adj_low <= d.put_wall_adj_p]
    bnc_p = (pierce_p.adj_close > pierce_p.put_wall_adj_p).mean() if len(pierce_p) > 10 else np.nan
    # fade-the-wall-touch trade: short at call_wall touch / long at put_wall touch, to close (next-bar = same day close)
    rc = pierce_c.call_wall_adj_p.sub(pierce_c.adj_close).div(pierce_c.call_wall_adj_p)  # short return to close
    rp = pierce_p.adj_close.sub(pierce_p.put_wall_adj_p).div(pierce_p.put_wall_adj_p)    # long return to close
    fade = pd.concat([rc, rp])
    fs = summ(fade)
    print(f"  [{label}] pin_gravitation={grav:.3f} (null .5) | call_reject={rej_c:.3f} (n{len(pierce_c)}) "
          f"| put_bounce={bnc_p:.3f} (n{len(pierce_p)})")
    if fs:
        print(f"           wall-touch fade-to-close: n={fs['n']} mean={fs['mean']:+.4f} "
              f"win={fs['win']:.3f} ex-top5%={fs['ex_top5']:+.4f}")


def main():
    df = load()
    des = df[df["date"] <= DESIGN_END]; hol = df[df["date"] > DESIGN_END]
    print(f"MSTR gamma: {len(df)} days {df.date.min()}..{df.date.max()} | design {len(des)} | holdout {len(hol)}")
    print(f"  regime mix: negGEX {(df.gex_sign<0).mean():.2f} of days; daily |r| median {df.r.abs().median():.3f}\n")
    print("== H1: gamma-regime conditional direction ==")
    h1(des, "DESIGN"); h1(hol, "HOLDOUT")
    print("\n== H3: gamma -> next-day vol / zero-gamma -> direction ==")
    h3(des, "DESIGN"); h3(hol, "HOLDOUT")
    print("\n== H2: daily wall reaction (pin gravitation / wall touch-reject, prior-day walls) ==")
    h2(des, "DESIGN"); h2(hol, "HOLDOUT")


if __name__ == "__main__":
    main()
