"""Is 'all cousins CONFIRMED' (the counterintuitive in-sample finding: confirmation beats divergence) STABLE, or
cherry-picked from in-sample noise?

A fixed rule has no parameters to train, so the honest test is consistency across INDEPENDENT slices. The rule was
spotted on ES -> NQ/YM/RTY are genuine out-of-sample (they didn't inform it). And each time period is independent.
For each market: R of reclaims where ALL 3 cousins also took their prior-day level (0 'held' on the d1 rung) vs
the all-reclaim baseline, with day-block CI, plus per-period consistency. Holds across markets + time = real.
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
TARGET = 3.0
ASSETS = [("ES", "events_es_tf.parquet", ["nq", "ym", "rty"]),
          ("NQ", "events_nq_tf.parquet", ["es", "ym", "rty"]),
          ("YM", "events_ym_tf.parquet", ["es", "nq", "rty"]),
          ("RTY", "events_rty_tf.parquet", ["es", "nq", "ym"])]
PERIODS = [("25Q4", 20251001, 20260101), ("26Q1", 20260101, 20260401), ("26Q2", 20260401, 20260701)]


def load(fn: str, cousins: list[str]) -> pd.DataFrame:
    df = pd.read_parquet(OUT / fn)
    df = df[df["sweep.5m.ever_reclaimed"].fillna(0).to_numpy() > 0].copy()
    df["r"] = seq_r(df, TARGET)
    t = pd.to_datetime(df["touch_ts_utc"], utc=True).dt.tz_convert("America/New_York")
    df["day"] = t.dt.date
    df["ymd"] = t.dt.strftime("%Y%m%d").astype(int)
    cols = [f"smt_tf.d1.{c}.mag" for c in cousins if f"smt_tf.d1.{c}.mag" in df.columns]
    df["held"] = (df[cols].to_numpy() > 0).sum(axis=1)          # cousins that diverged (did NOT take their level)
    df["allconf"] = df["held"] == 0                            # all 3 cousins also took their level
    return df


def main() -> int:
    print(f"ALL-CONFIRMED reclaim R vs baseline @ {TARGET}R (rule found on ES; NQ/YM/RTY are OOS):\n")
    for name, fn, cousins in ASSETS:
        if not (OUT / fn).exists():
            print(f"{name}: {fn} missing -- skip")
            continue
        df = load(fn, cousins)
        bm, bl, bh = boot(df["r"].to_numpy(), df["day"].to_numpy())
        ac = df[df["allconf"]]
        if len(ac) < 20:
            print(f"{name}: all-confirmed thin ({len(ac)})")
            continue
        am, al, ah = boot(ac["r"].to_numpy(), ac["day"].to_numpy())
        tag = "OOS" if name != "ES" else "in-sample"
        flag = "  <== clears 0" if al > 0 else ""
        print(f"{name} ({tag}): baseline {bm:+.2f}[{bl:+.2f},{bh:+.2f}] n{len(df)}   "
              f"ALL-CONFIRMED {am:+.2f}[{al:+.2f},{ah:+.2f}] n{len(ac)}{flag}")
        cells = []
        for plab, ps, pe in PERIODS:
            s = ac[(ac["ymd"] >= ps) & (ac["ymd"] < pe)]
            b = df[(df["ymd"] >= ps) & (df["ymd"] < pe)]
            if len(s) < 12:
                cells.append(f"{plab} n<12")
                continue
            cells.append(f"{plab} {s['r'].mean():+.2f}(n{len(s)})/base{b['r'].mean():+.2f}")
        print(f"     by period: {'  |  '.join(cells)}")
    print("\nREAD: all-confirmed beats baseline on the 3 OOS markets too, and is positive every period = the weird "
          "'confirmation > divergence' result is REAL. Patchy / only-ES / flips by period = in-sample artifact.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
