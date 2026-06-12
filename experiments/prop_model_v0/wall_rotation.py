"""WALL ROTATION (Ben's intraday sequence idea): touch + reject one wall -> trade
the rotation to the OTHER wall.

Event: first intraday touch of either (prior-day) wall on ES 1m. Rejection confirm =
price retraces 15% of the wall-to-wall width back from the touched extreme. Entry on
the confirm, direction = toward the far wall. Outcomes measured to the close:
  REAL:    target = the opposite wall;     stop = touched extreme +/- 25% width
  PLACEBO: target = same DISTANCE as the real target but measured from entry in the
           same direction with no wall there (entry +/- dist) — isolates "the wall
           attracts" from "mornings mean-revert by this magnitude".
Also: raw second-leg stats — P(reach far wall | touch+reject) vs P(re-break first).

Run: backend/.venv/Scripts/python.exe experiments/prop_model_v0/wall_rotation.py
Artifact: report/wall_rotation.md
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

MODULE = Path(__file__).resolve().parent
sys.path.insert(0, str(MODULE))
from features_index import load_es_minutes  # noqa: E402

sys.path.insert(0, str(MODULE.parents[0] / "btc_model_v0"))
from model_wf import week_boot_p  # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:  # noqa: BLE001
    pass

COST_PTS = 2.0
RETRACE = 0.15  # rejection confirm: 15% of wall width back from the extreme
STOP_W = 0.25  # stop: 25% of width beyond the touched extreme


def resolve(seg, entry, tgt, stp, long: bool):
    ht = np.flatnonzero(seg >= tgt) if long else np.flatnonzero(seg <= tgt)
    hs = np.flatnonzero(seg <= stp) if long else np.flatnonzero(seg >= stp)
    it = ht[0] if len(ht) else 10**12
    is_ = hs[0] if len(hs) else 10**12
    risk = abs(entry - stp)
    if is_ <= it and is_ < 10**12:
        pnl = -risk
    elif it < 10**12:
        pnl = abs(tgt - entry)
    else:
        pnl = (seg[-1] - entry) * (1 if long else -1)
    return (pnl - COST_PTS) / risk


def main() -> int:
    w = pd.read_parquet(MODULE / "data" / "walls_deep.parquet")
    w.index = pd.to_datetime(w["date"], format="%Y%m%d")
    f = pd.read_parquet(MODULE / "data" / "features_es.parquet")
    es_close = f["c_px"]
    prev = w[["call_wall", "put_wall", "spot"]].reindex(f.index).shift(1)
    ratio = es_close.shift(1) / prev["spot"]
    cw_s, pw_s = prev["call_wall"] * ratio, prev["put_wall"] * ratio

    m = load_es_minutes("ES.c.0")
    ets = pd.DatetimeIndex(m.index.tz_localize(None))
    ec = m["c"].to_numpy(float)
    mtd = m["td"].to_numpy()
    days = f.index.to_numpy()
    starts = np.searchsorted(mtd, days)
    stats, trades = [], []
    for i, d in enumerate(f.index):
        cw, pw = cw_s.iloc[i], pw_s.iloc[i]
        if not (np.isfinite(cw) and np.isfinite(pw) and cw > pw):
            continue
        a = starts[i]
        b = starts[i + 1] if i + 1 < len(days) else len(ec)
        seg = ec[a:b]
        if len(seg) < 100:
            continue
        width = cw - pw
        if not (pw < seg[0] < cw):  # start inside the range (no gap-through entries)
            continue
        hc = np.flatnonzero(seg >= cw)
        hp = np.flatnonzero(seg <= pw)
        ic_ = hc[0] if len(hc) else 10**12
        ip_ = hp[0] if len(hp) else 10**12
        first = min(ic_, ip_)
        if first == 10**12:
            stats.append({"d": d, "event": "no_touch"})
            continue
        upper = ic_ < ip_
        t0 = int(first)
        # rejection confirm after the touch: retrace 15% of width from the extreme
        post = seg[t0:]
        if upper:
            ext = post[: max(np.argmax(post), 1) + 1].max()
            conf = np.flatnonzero(post <= ext - RETRACE * width)
        else:
            ext = post[: max(np.argmin(post), 1) + 1].min()
            conf = np.flatnonzero(post >= ext + RETRACE * width)
        if not len(conf):
            stats.append({"d": d, "event": "touch_no_reject", "upper": upper})
            continue
        e0 = t0 + int(conf[0])
        entry = seg[e0]
        rest = seg[e0:]
        far = pw if upper else cw
        reach_far = (rest <= far).any() if upper else (rest >= far).any()
        rebreak = (rest >= ext).any() if upper else (rest <= ext).any()
        stats.append(
            {
                "d": d,
                "event": "reject",
                "upper": upper,
                "reach_far": bool(reach_far),
                "rebreak_first": bool(rebreak and not reach_far),
            }
        )
        long = not upper
        stp = (ext + STOP_W * width) if upper else (ext - STOP_W * width)
        dist = abs(entry - far)
        trades.append(
            {
                "d": d,
                "upper": upper,
                "entry": entry,
                "dist": dist,
                "rest_a": e0 + (starts[i]),
                "i": i,
                "real": resolve(rest, entry, far, stp, long),
                "stp": stp,
            }
        )
    st = pd.DataFrame(stats)
    tr = pd.DataFrame(trades)
    # PROPER placebo: shuffle target DISTANCES across trades (same distance
    # distribution, decoupled from each day's actual wall location)
    rng = np.random.default_rng(5)
    shuf = rng.permutation(tr["dist"].to_numpy())
    plc_r = []
    for k, (_, row) in enumerate(tr.iterrows()):
        a2 = int(row["rest_a"])
        b2 = starts[int(row["i"]) + 1] if int(row["i"]) + 1 < len(days) else len(ec)
        rest = ec[a2:b2]
        long = not bool(row["upper"])
        plc = row["entry"] + shuf[k] * (1 if long else -1)
        plc_r.append(resolve(rest, row["entry"], plc, row["stp"], long))
    tr["placebo"] = plc_r
    rj = st[st["event"] == "reject"]
    lines = [
        "# Wall rotation — touch/reject one wall, trade to the other",
        "",
        f"days with walls + inside-range open: {len(st)} | touches: "
        f"{int((st['event'] != 'no_touch').sum())} | rejections (tradeable events): {len(rj)}",
        f"P(reach far wall | rejection): {rj['reach_far'].mean():.0%} | "
        f"P(re-break first): {rj['rebreak_first'].mean():.0%}",
        "",
    ]
    if len(tr) >= 30:
        wk = pd.DatetimeIndex(tr["d"]).to_period("W").astype(str).to_numpy()
        for c in ("real", "placebo"):
            net = tr[c].to_numpy(float)
            lines.append(
                f"{c:8s} target: n={len(tr)}, mean net R {net.mean():+.3f}, "
                f"wk p5 {week_boot_p(net, wk, 5):+.3f}"
            )
        lines.append(
            f"wall-identity premium (real - placebo): "
            f"{(tr['real'] - tr['placebo']).mean():+.3f} R"
        )
        era = pd.DatetimeIndex(tr["d"]) >= pd.Timestamp("2024-07-01")
        lines.append(
            f"era subset n={int(era.sum())}: real {tr.loc[era, 'real'].mean():+.3f} "
            f"vs placebo {tr.loc[era, 'placebo'].mean():+.3f}"
        )
    report = "\n".join(lines)
    (MODULE / "report" / "wall_rotation.md").write_text(report, encoding="utf-8")
    print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
