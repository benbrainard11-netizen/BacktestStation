"""ANGLE 3 — CAUSAL cross-asset (NQ+ES+YM+RTY) lead-lag / relative-strength / SMT features.

Keyed to the existing dataset_ndx.parquet decisions (date, ms). For every decision at
time `ms` (ms-of-day ET) on `date`, build features from the 1m bars of all four index
futures using ONLY bars fully closed by the decision time.

CAUSALITY (hard rule 1): ts_event is the bar OPEN time (databento). The bar opening at
et=T covers [T, T+1min) and is only fully CLOSED at T+1min. So at decision ms we may use
bars with  et_ms <= ms - 60000  (last fully-closed bar). assert_no_lookahead enforced.

Writes a UNIQUE file: out/dirhunt_xasset.parquet  (never touches shared artifacts).

Feature families (all causal, computed at decision time t):
  xa_ret_{sym}_{w}   — log return of sym over last w closed minutes (w in 1,3,5,15,30)
  xa_rs_nq_{sym}_{w} — NQ ret minus sym ret over last w min (relative strength)
  xa_lead_{sym}      — does sym's most-recent 1m move "lead" (corr of sym ret_{t} vs NQ ret_{t}
                       is positive historically; here we expose the cross-asset move itself as a
                       contemporaneous-but-causal predictor of NQ's NEXT move)
  xa_beta_resid_{sym}— NQ residual vs a rolling regression on sym (NQ richer/poorer than peers)
  xa_smt_{sym}_{tf}  — proper SMT divergence NQ vs sym at swing pivots (tf in 5,15 min), signed
  xa_breadth_up      — # of {ES,YM,RTY} up over last 5 min (0..3); breadth confirm/diverge
  xa_disp            — cross-asset dispersion (std of the 4 normalized 5-min returns)
  xa_nq_vs_breadth   — sign(NQ 5m ret) vs breadth majority (NQ leading or lagging the pack)
"""
from __future__ import annotations

import sys
from datetime import date as Date, time as Time, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common as C

ET = ZoneInfo(C.ET)
OUT = Path(__file__).resolve().parent / "out"
SYMS = {"nq": C.BARS_1M_ROOT / "symbol=NQ.c.0",
        "es": C.BARS_1M_ROOT / "symbol=ES.c.0",
        "ym": C.BARS_1M_ROOT / "symbol=YM.c.0",
        "rty": C.BARS_1M_ROOT / "symbol=RTY.c.0"}
WINDOWS = [1, 3, 5, 15, 30]
PEERS = ["es", "ym", "rty"]


def load_day_et(root: Path, day: Date) -> pd.DataFrame | None:
    p = root / f"date={day.isoformat()}" / "part-000.parquet"
    if not p.exists():
        return None
    df = pd.read_parquet(p, columns=["ts_event", "open", "high", "low", "close", "volume"])
    df["et"] = df["ts_event"].dt.tz_convert(ET)
    # ms-of-day of the bar OPEN; bar is CLOSED at this open-ms + 60000
    e = df["et"]
    df["open_ms"] = (e.dt.hour * 3600 + e.dt.minute * 60 + e.dt.second) * 1000
    df["close_ms"] = df["open_ms"] + 60000
    return df.sort_values("et").reset_index(drop=True)


def fractal_pivots(low: np.ndarray, high: np.ndarray, k: int):
    n = len(low)
    lo_piv, hi_piv = [], []
    for i in range(k, n - k):
        wl = low[i - k:i + k + 1]
        wh = high[i - k:i + k + 1]
        if low[i] == wl.min() and (low[i] < low[i - 1] or low[i] < low[i + 1]):
            lo_piv.append(i)
        if high[i] == wh.max() and (high[i] > high[i - 1] or high[i] > high[i + 1]):
            hi_piv.append(i)
    return np.array(lo_piv, int), np.array(hi_piv, int)


def smt_signed(nq: pd.DataFrame, peer: pd.DataFrame, upto_idx_nq: int, upto_idx_peer: int,
               k: int = 3, fresh: int = 20) -> int:
    """Proper SMT: at last 2 confirmed swing lows/highs visible by decision, does NQ make a
    new extreme while peer fails (or vice versa)? Returns signed bias for NQ's next move.

    Bullish SMT (+1): NQ makes lower-low but peer makes higher-low  -> NQ oversold vs peer (bounce).
    Bearish SMT (-1): NQ makes higher-high but peer makes lower-high -> NQ overbought vs peer (fade).
    Only pivots confirmed (p <= idx-k) are visible. Aligns the two series by close_ms.
    """
    if upto_idx_nq < 2 * k + 2 or upto_idx_peer < 2 * k + 2:
        return 0
    nl, nh = nq["low"].to_numpy()[:upto_idx_nq + 1], nq["high"].to_numpy()[:upto_idx_nq + 1]
    pl, ph = peer["low"].to_numpy()[:upto_idx_peer + 1], peer["high"].to_numpy()[:upto_idx_peer + 1]
    n_close = nq["close_ms"].to_numpy()[:upto_idx_nq + 1]
    p_close = peer["close_ms"].to_numpy()[:upto_idx_peer + 1]
    nlo, nhi = fractal_pivots(nl, nh, k)
    cutoff = upto_idx_nq - k
    nlo = nlo[nlo <= cutoff]
    nhi = nhi[nhi <= cutoff]
    out = 0
    # peer index aligned by close_ms (asof backward) — peer value AT the NQ pivot time
    def peer_at(ms, arr):
        j = np.searchsorted(p_close, ms, side="right") - 1
        return arr[j] if j >= 0 else np.nan
    if len(nlo) >= 2 and (upto_idx_nq - nlo[-1]) <= fresh:
        p1, p2 = nlo[-2], nlo[-1]
        pe1, pe2 = peer_at(n_close[p1], pl), peer_at(n_close[p2], pl)
        if np.isfinite(pe1) and np.isfinite(pe2):
            if nl[p2] < nl[p1] and pe2 > pe1:        # NQ LL, peer HL -> bullish for NQ
                out = 1
    if len(nhi) >= 2 and (upto_idx_nq - nhi[-1]) <= fresh:
        p1, p2 = nhi[-2], nhi[-1]
        pe1, pe2 = peer_at(n_close[p1], ph), peer_at(n_close[p2], ph)
        if np.isfinite(pe1) and np.isfinite(pe2):
            if nh[p2] > nh[p1] and pe2 < pe1:        # NQ HH, peer LH -> bearish for NQ
                out = -1 if out == 0 else 0
    return out


def feats_for_day(day: Date, decisions_ms: list[int]) -> list[dict]:
    days_bars = {s: load_day_et(r, day) for s, r in SYMS.items()}
    if days_bars["nq"] is None:
        return []
    rows = []
    for ms in decisions_ms:
        # last fully-CLOSED bar per symbol: close_ms <= ms  (i.e. open_ms <= ms-60000)
        feat = {"date": day.isoformat(), "ms": ms}
        closed = {}
        last_close_ts = {}
        ok = True
        for s, b in days_bars.items():
            if b is None:
                closed[s] = None
                continue
            mask = b["close_ms"].to_numpy() <= ms
            idx = np.nonzero(mask)[0]
            if len(idx) == 0:
                closed[s] = None
                if s == "nq":
                    ok = False
                continue
            ci = idx[-1]
            closed[s] = (b, ci)
            # record latest feature ts (bar OPEN ts of last closed bar) for lookahead assert
            last_close_ts[s] = b["et"].iloc[ci]
        if not ok or closed["nq"] is None:
            continue
        # ---- lookahead assert: every used bar's CLOSE time <= decision time ----
        dec_dt = pd.Timestamp(datetime.combine(day, Time(*divmod_hms(ms)), tzinfo=ET))
        for s, v in closed.items():
            if v is None:
                continue
            b, ci = v
            close_dt = b["et"].iloc[ci] + pd.Timedelta(minutes=1)  # bar closes 1 min after open
            C.assert_no_lookahead(close_dt, dec_dt, f"xa_{s}")

        # ---- per-symbol returns over windows (using closes of fully-closed bars) ----
        rets = {}  # rets[s][w] = log return of sym over last w closed minutes
        for s, v in closed.items():
            rets[s] = {}
            if v is None:
                for w in WINDOWS:
                    rets[s][w] = np.nan
                continue
            b, ci = v
            cl = b["close"].to_numpy()
            for w in WINDOWS:
                if ci - w >= 0 and cl[ci - w] > 0 and cl[ci] > 0:
                    rets[s][w] = float(np.log(cl[ci] / cl[ci - w]))
                else:
                    rets[s][w] = np.nan

        for s in SYMS:
            for w in WINDOWS:
                feat[f"xa_ret_{s}_{w}"] = rets[s][w]
        # relative strength: NQ minus peer over each window
        for s in PEERS:
            for w in WINDOWS:
                a, b_ = rets["nq"][w], rets[s][w]
                feat[f"xa_rs_nq_{s}_{w}"] = (a - b_) if (np.isfinite(a) and np.isfinite(b_)) else np.nan
        # breadth: # peers up over last 5 closed min
        ups = [1 for s in PEERS if np.isfinite(rets[s][5]) and rets[s][5] > 0]
        dns = [1 for s in PEERS if np.isfinite(rets[s][5]) and rets[s][5] < 0]
        feat["xa_breadth_up"] = float(len(ups))
        feat["xa_breadth_net"] = float(len(ups) - len(dns))
        # dispersion: std of the 4 5-min returns (vol-normalized regime)
        r5 = [rets[s][5] for s in SYMS if np.isfinite(rets[s][5])]
        feat["xa_disp"] = float(np.std(r5)) if len(r5) >= 2 else np.nan
        # NQ leads/lags pack: sign(NQ 5m) vs breadth majority
        nq5 = rets["nq"][5]
        if np.isfinite(nq5):
            maj = np.sign(len(ups) - len(dns))
            feat["xa_nq_vs_breadth"] = float(np.sign(nq5) - maj)  # 0 aligned, +-1/2 diverge
        else:
            feat["xa_nq_vs_breadth"] = np.nan
        # peer momentum that "leads" NQ: average peer 1m and 3m return (the freshest peer push)
        for w in (1, 3):
            vals = [rets[s][w] for s in PEERS if np.isfinite(rets[s][w])]
            feat[f"xa_peer_mom_{w}"] = float(np.mean(vals)) if vals else np.nan
        # peer-minus-NQ freshest: peers moved but NQ hasn't yet (catch-up lead-lag)
        for w in (1, 3):
            vals = [rets[s][w] for s in PEERS if np.isfinite(rets[s][w])]
            if vals and np.isfinite(rets["nq"][w]):
                feat[f"xa_peer_lead_{w}"] = float(np.mean(vals) - rets["nq"][w])
            else:
                feat[f"xa_peer_lead_{w}"] = np.nan
        # proper SMT vs each peer at 5m and 15m equivalent (use 1m pivots; tf via k/fresh)
        for s in PEERS:
            v = closed[s]
            if v is None:
                feat[f"xa_smt_{s}"] = 0.0
                continue
            pb, pci = v
            nb, nci = closed["nq"]
            feat[f"xa_smt_{s}"] = float(smt_signed(nb, pb, nci, pci, k=3, fresh=20))
        # SMT consensus across peers
        sv = [feat[f"xa_smt_{s}"] for s in PEERS]
        feat["xa_smt_sum"] = float(np.sum(sv))
        rows.append(feat)
    return rows


def divmod_hms(ms: int):
    h, rem = divmod(ms // 1000, 3600)
    return h, rem // 60, rem % 60


def main() -> int:
    df = pd.read_parquet(OUT / "dataset_ndx.parquet")
    assert df["date"].max() < "2026-04-01", "HOLDOUT LEAK"
    by_day = df.groupby("date")["ms"].apply(list)
    all_rows = []
    ndays = len(by_day)
    for i, (d, mss) in enumerate(by_day.items()):
        day = Date.fromisoformat(d)
        all_rows.extend(feats_for_day(day, sorted(mss)))
        if (i + 1) % 25 == 0:
            print(f"  {i+1}/{ndays} days, {len(all_rows)} rows")
    out = pd.DataFrame(all_rows)
    out.to_parquet(OUT / "dirhunt_xasset.parquet", index=False)
    print("wrote", OUT / "dirhunt_xasset.parquet", out.shape)
    print("feature cols:", [c for c in out.columns if c.startswith("xa_")])
    print(out.describe().T[["mean", "std", "min", "max"]].round(4).to_string())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
