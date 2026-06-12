"""Defender family — LATE TAKER test ("follow a portion of their move").

The maker test failed for a measured reason: the defender reaction resolves in ~7s
median and the (12,4) race is decided inside quote noise; makers fill on the break,
queue fills arrive after the winners left. The implementable alternative: enter AT
MARKET shortly after detection — zero fill ambiguity, latency-tolerant by design —
with entry-relative geometry wide enough to clear thin-book noise.

PRE-STATED (before this first run): entry ladder L in {10s, 30s, 60s} after ts_define
(all three reported; no post-hoc pick — the ladder maps the decay), direction = join
the defender, entry price = the touched side's quote (buy at ask / sell at bid =
spread paid inside the measurement), geometry (k=16, j=8) ticks entry-relative,
horizon 60m, costs = commission + 1 tick stop slip. Events: NQ/RTY confirmation
window (3rd construction explored on this window for this family — disclosed; the
sealed holdout remains the final arbiter for whatever is pinned).

Run: backend/.venv/Scripts/python.exe experiments/level_scalp_v0/defender_late_taker.py
Artifact: report/defender_late_taker.md
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from spec import MODULE, OUT, TICK  # noqa: E402
from atlas_report import block_boot, comm_ticks, md_table  # noqa: E402
from outcomes import touch_outcomes  # noqa: E402
from touches import load_day_quotes  # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:  # noqa: BLE001
    pass

LADDER_S = [10, 30, 60]
K, J = 16, 8
STRESS = 1  # tick of stop slip
HORIZON_S = 3600


def main() -> int:
    ev = pd.read_parquet(OUT / "defender_events.parquet")
    ev = ev[ev["symbol"].isin(["NQ.c.0", "RTY.c.0"])]
    rows: list[dict] = []
    for sym, sub in ev.groupby("symbol"):
        tick = TICK[sym]
        for d, day_ev in sub.groupby("trading_day"):
            quotes = load_day_quotes(sym, d)
            if quotes is None:
                continue
            ts, bid, ask, mid, _, _ = quotes
            for e in day_ev.itertuples(index=False):
                buy = e.side == "B"
                for lag in LADDER_S:
                    i0 = int(
                        ts.searchsorted(
                            pd.Timestamp(e.ts_define) + pd.Timedelta(seconds=lag)
                        )
                    )
                    if i0 >= len(ts) - 2:
                        continue
                    entry = float(ask[i0]) if buy else float(bid[i0])
                    o = touch_outcomes(
                        ts,
                        bid,
                        ask,
                        mid,
                        i0,
                        len(ts),
                        level=entry,
                        from_below=not buy,
                        tick=tick,
                        horizon_s=HORIZON_S,
                    )
                    if o is None:
                        continue
                    tw, tl = o[f"t_win_{K}"], o[f"t_loss_{J}"]
                    win = not np.isnan(tw) and (np.isnan(tl) or tw < tl)
                    loss = not np.isnan(tl) and (np.isnan(tw) or tl <= tw)
                    gross = (
                        float(K)
                        if win
                        else (-(float(J + STRESS)) if loss else o["g_end"])
                    )
                    rows.append(
                        {
                            "symbol": sym,
                            "trading_day": e.trading_day,
                            "lag": lag,
                            "ev": gross - comm_ticks(sym),
                            "outcome": "win" if win else ("loss" if loss else "time"),
                        }
                    )
    df = pd.DataFrame(rows)
    lines = [f"# Defender late-taker ladder — (k={K}, j={J}) entry-relative, 60m", ""]
    stats = []
    for (sym, lag), g in df.groupby(["symbol", "lag"]):
        days = g["trading_day"].astype(str).to_numpy()
        means, _ = block_boot(g["ev"].to_numpy(float)[:, None], days)
        stats.append(
            {
                "symbol": sym,
                "lag_s": lag,
                "n": len(g),
                "net": round(float(g["ev"].mean()), 2),
                "p5": round(float(np.percentile(means, 5)), 2),
                "win%": round(float((g["outcome"] == "win").mean()), 2),
                "time%": round(float((g["outcome"] == "time").mean()), 2),
            }
        )
    tab = pd.DataFrame(stats)
    lines += [
        md_table(tab),
        "",
        "Entry at the touched-side quote => the spread is paid inside the number.",
        "Net of commission + 1 tick stop slip. No post-hoc lag selection.",
    ]
    report = "\n".join(lines)
    (MODULE / "report" / "defender_late_taker.md").write_text(report, encoding="utf-8")
    print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
