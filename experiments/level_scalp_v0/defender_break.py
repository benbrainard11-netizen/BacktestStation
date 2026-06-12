"""Defense-break continuation — the INVERSION (4th construction on this window; disclosed).

Motivation (two independent diagnostics, not a grid scan): Phase 1 found proof-fills at
levels predict continuation; the defender fills run found through-fills 97-98% "stopped"
= price ran 4+ more ticks in the break direction, averaging ~9 ticks past the defended
price. This tests the trade those numbers imply: when a DETECTED defense visibly fails
(first trade strictly through the defended price within 60m of detection), enter AT
MARKET in the break direction and ride minutes-scale continuation.

PRE-STATED single primary (before first run): entry = touched-side quote at break
detection (spread paid inside), geometry (k=8, j=8) entry-relative, horizon 30m,
costs = commission + 1 tick stop slip. PRIMARY population: NQ+RTY pooled (where
defenders were informative); ES reported separately (its defenders were null for
joining). Secondary descriptive: (12,8), (16,8), (6,6). The sealed holdout remains
the only confirmatory window for whatever gets pinned from this family.

Run: backend/.venv/Scripts/python.exe experiments/level_scalp_v0/defender_break.py
Artifact: report/defender_break.md
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from spec import MODULE, OUT, TICK  # noqa: E402
from atlas_report import block_boot, comm_ticks, md_table  # noqa: E402
from mode_a_sim import load_mbp1_day, trade_through_fill  # noqa: E402
from outcomes import touch_outcomes  # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:  # noqa: BLE001
    pass

PRIMARY_KJ = (8, 8)
SECONDARY = [(12, 8), (16, 8), (6, 6)]
HORIZON_S = 1800
BREAK_WINDOW_MIN = 60
STRESS = 1


def main() -> int:
    ev = pd.read_parquet(OUT / "defender_events.parquet")
    rows: list[dict] = []
    for (sym, d), day_ev in ev.groupby(["symbol", "trading_day"]):
        tick = TICK[sym]
        mb = load_mbp1_day(sym, d)
        if mb is None:
            continue
        ts, act, f = mb
        bid, ask, mid = f["bid_px"], f["ask_px"], (f["bid_px"] + f["ask_px"]) / 2.0
        for e in day_ev.itertuples(index=False):
            t_def = pd.Timestamp(e.ts_define)
            pi = int(ts.searchsorted(t_def))
            hi = min(
                int(ts.searchsorted(t_def + pd.Timedelta(minutes=BREAK_WINDOW_MIN))),
                len(ts),
            )
            if hi - pi < 2:
                continue
            # break of a defending BID = downward trade-through (buy=True detector);
            # break of a defending ASK = upward. The break trade goes WITH the break.
            defending_bid = e.side == "B"
            t_break = trade_through_fill(
                ts, act, f, e.price, defending_bid, pi, hi, tick
            )
            broke = t_break is not None
            r = {
                "symbol": sym,
                "trading_day": e.trading_day,
                "price": e.price,
                "side": e.side,
                "broke": broke,
            }
            if broke:
                ib = int(ts.searchsorted(t_break))
                if ib < len(ts) - 2:
                    short = defending_bid  # bid broke -> go short; ask broke -> long
                    entry = float(bid[ib]) if short else float(ask[ib])
                    o = touch_outcomes(
                        ts,
                        bid,
                        ask,
                        mid,
                        ib,
                        len(ts),
                        level=entry,
                        from_below=short,
                        tick=tick,
                        horizon_s=HORIZON_S,
                    )
                    if o is not None:
                        r["break_latency_s"] = float((t_break - t_def).total_seconds())
                        for k, j in [PRIMARY_KJ, *SECONDARY]:
                            tw, tl = o[f"t_win_{k}"], o[f"t_loss_{j}"]
                            win = not np.isnan(tw) and (np.isnan(tl) or tw < tl)
                            loss = not np.isnan(tl) and (np.isnan(tw) or tl <= tw)
                            r[f"ev_{k}_{j}"] = (
                                float(k)
                                if win
                                else (-(float(j + STRESS)) if loss else o["g_end"])
                            )
                            r[f"win_{k}_{j}"] = bool(win)
            rows.append(r)
    df = pd.DataFrame(rows)

    lines = ["# Defense-break continuation — pre-stated (8,8)@30m taker", ""]
    stats = []
    trades = df[df.get("ev_8_8").notna()] if "ev_8_8" in df else df.iloc[0:0]
    for pop, sub in [
        ("NQ+RTY (PRIMARY)", trades[trades["symbol"].isin(["NQ.c.0", "RTY.c.0"])]),
        ("ES (secondary)", trades[trades["symbol"] == "ES.c.0"]),
    ]:
        if len(sub) < 30:
            stats.append({"population": pop, "n": len(sub), "note": "insufficient n"})
            continue
        ct = sub["symbol"].map(comm_ticks).to_numpy(float)
        days = sub["trading_day"].astype(str).to_numpy()
        row = {
            "population": pop,
            "n_breaks": len(sub),
            "break_rate": round(
                len(sub)
                / max(
                    int(df[df["symbol"].isin(sub["symbol"].unique())]["broke"].count()),
                    1,
                ),
                2,
            ),
        }
        for k, j in [PRIMARY_KJ, *SECONDARY]:
            net = sub[f"ev_{k}_{j}"].to_numpy(float) - ct
            means, _ = block_boot(net[:, None], days)
            tag = "PRIM" if (k, j) == PRIMARY_KJ else "sec"
            row[f"{tag}({k},{j})_net"] = round(float(net.mean()), 2)
            row[f"{tag}({k},{j})_p5"] = round(float(np.percentile(means, 5)), 2)
            row[f"{tag}({k},{j})_win%"] = round(float(sub[f"win_{k}_{j}"].mean()), 2)
        row["med_break_latency_s"] = round(float(sub["break_latency_s"].median()), 0)
        stats.append(row)
        # also: overall break frequency for context
    tab = pd.DataFrame(stats)
    lines += [
        md_table(tab),
        "",
        f"Events that broke within {BREAK_WINDOW_MIN}m of detection: "
        f"{int(df['broke'].sum())}/{len(df)} ({df['broke'].mean():.0%}).",
        "Entry at touched-side quote at break detection (spread inside); net of",
        f"commission + {STRESS} tick stop slip; horizon {HORIZON_S // 60}m; stop wins ties.",
    ]
    report = "\n".join(lines)
    (MODULE / "report" / "defender_break.md").write_text(report, encoding="utf-8")
    print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
