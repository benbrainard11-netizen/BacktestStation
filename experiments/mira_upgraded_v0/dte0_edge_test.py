"""Does the INTRADAY 0DTE gamma context AT THE ENTRY MINUTE condition the reclaim edge? net 0DTE gamma sign
(positive=pin/revert, negative=squeeze/trend) + whether price sits AT the 0DTE pin. Naturally no-lookahead --
the intraday GEX at the entry instant is known in real time. Reads events_es_tf + dte0_intraday_spx.parquet.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

sys.path.insert(0, str(Path(__file__).resolve().parent))
from reclaim_entry import boot, seq_r  # noqa: E402

OUT = Path(__file__).resolve().parent / "out"
GEX = Path(__file__).resolve().parents[1] / "options_signals_v0" / "out"
TARGET = 3.0


def _split(d: pd.DataFrame, label: str, groups) -> None:
    print(label)
    for name, mask in groups:
        s = d[mask.fillna(False).to_numpy()]
        if len(s) < 20:
            print(f"   {name:20} n<20 ({len(s)})")
            continue
        m, lo, hi = boot(s["r"].to_numpy(), s["day"].to_numpy())
        print(f"   {name:20} {m:+.2f} [{lo:+.2f},{hi:+.2f}]  n{len(s)}")


def main() -> int:
    df = pd.read_parquet(OUT / "events_es_tf.parquet")
    df = df[df["sweep.5m.ever_reclaimed"].fillna(0).to_numpy() > 0].copy()
    df["r"] = seq_r(df, TARGET)
    t = pd.to_datetime(df["touch_ts_utc"], utc=True).dt.tz_convert("America/New_York")
    df["day"] = t.dt.date
    df["key"] = (t.dt.strftime("%Y%m%d").astype(int) * 1440 + t.dt.hour * 60 + t.dt.minute)   # date+minute key

    g = pd.read_parquet(GEX / "dte0_intraday_spx.parquet")
    g["key"] = g["date"].astype(int) * 1440 + (g["ms_of_day"] // 60000)
    for col in ("net_gex", "pin", "spot"):
        df[f"dte_{col}"] = df["key"].map(g.set_index("key")[col].to_dict())
    d = df.dropna(subset=["dte_net_gex"]).copy()
    bm, bl, bh = boot(d["r"].to_numpy(), d["day"].to_numpy())
    print(f"reclaim events with intraday 0DTE GEX at entry: {len(d)}")
    print(f"baseline reclaim R: {bm:+.2f} [{bl:+.2f},{bh:+.2f}]\n")

    _split(d, "by 0DTE net-gamma sign at the entry minute:",
           [("positive (pin/revert)", d["dte_net_gex"] > 0), ("negative (squeeze)", d["dte_net_gex"] <= 0)])

    d["dist_pin"] = (d["dte_spot"] - d["dte_pin"]).abs()
    print()
    _split(d, "by proximity to the 0DTE pin (price sitting on the high-gamma strike):",
           [("AT pin (<=10pt)", d["dist_pin"] <= 10), ("away (>10pt)", d["dist_pin"] > 10)])

    print("\nREAD: a split clearly off the flat baseline = intraday 0DTE positioning conditions the edge -- the thing "
          "the daily GEX could never see. Flat across = even the fast signal doesn't separate reclaim reverts vs fails.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
