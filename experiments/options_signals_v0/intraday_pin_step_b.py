"""FREE Step B: does ES pin to the SPX gamma wall in the FINAL HOUR (15:00->16:00 ET),
vs a CONTROL hour (10:00->11:00 ET), split by gamma sign?

Finer-resolution follow-up to intraday_pin.py's open->close screen, which was NULL
(53-54% toward-wall, no gamma-sign separation). 0DTE pinning is strongest into the cash
close, so if it's real it should show in the FINAL HOUR and NOT the control hour, and be
stronger on positive-gamma days (dealers long gamma -> suppress -> pin) than negative-gamma.
This is the last FREE test before any minute-OPRA spend. No new data: reuses build_walls()
(SPX chains we already own) + 1m ES bars from the warehouse.

Run: backend/.venv/Scripts/python.exe experiments/options_signals_v0/intraday_pin_step_b.py
"""
from __future__ import annotations

import datetime as dt
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, "backend")
from app.data.reader import read_bars  # noqa: E402

ET = "America/New_York"
OUT = Path("experiments/options_signals_v0/out")
WALL_CACHE = OUT / "gamma_walls_2025.parquet"
START, END = dt.date(2025, 1, 1), dt.date(2025, 12, 31)


def get_walls() -> pd.DataFrame:
    """Daily dominant SPX gamma wall + gamma sign. Cached; first build is the slow DBN read."""
    if WALL_CACHE.exists():
        return pd.read_parquet(WALL_CACHE)
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from intraday_pin import build_walls  # noqa: E402

    wl = build_walls()
    wl.to_parquet(WALL_CACHE)
    return wl


def es_close_et() -> pd.Series:
    """All 2025 ES 1m closes, indexed by ET timestamp (sorted)."""
    df = read_bars(symbol="ES.c.0", timeframe="1m", start=START, end=END)
    ts = pd.to_datetime(df["ts_event"], utc=True).dt.tz_convert(ET)
    return pd.Series(df["close"].to_numpy(), index=ts).sort_index()


def pulls(es: pd.Series, walls: pd.DataFrame, a: tuple[int, int], b: tuple[int, int]) -> pd.DataFrame:
    """Signed pull toward the wall from clock-mark a to clock-mark b (asof prices), per wall day,
    normalized by spot. pull > 0 = price moved CLOSER to the wall over [a, b]."""
    by_day = {ts.date(): g for ts, g in es.groupby(es.index.normalize())}
    rows = []
    for d, w in walls.iterrows():
        day = pd.Timestamp(d).date()
        g = by_day.get(day)
        if g is None or len(g) == 0:
            continue

        def price_at(hm: tuple[int, int]) -> float:
            t = pd.Timestamp(day, tz=ET) + pd.Timedelta(hours=hm[0], minutes=hm[1])
            s = g[g.index <= t]  # asof: last trade at/before the mark
            return float(s.iloc[-1]) if len(s) else np.nan

        pa, pb = price_at(a), price_at(b)
        if not (np.isfinite(pa) and np.isfinite(pb)):
            continue
        pull = (abs(pa - w["wall"]) - abs(pb - w["wall"])) / w["spot"]
        rows.append({"date": pd.Timestamp(day), "pull": pull, "pos_gamma": bool(w["pos_gamma"])})
    return pd.DataFrame(rows).set_index("date")


def report(name: str, df: pd.DataFrame) -> None:
    print(f"\n{name}:  (pull>0 = moved toward the wall)")
    for lbl, sub in [
        ("positive-gamma (should PIN)", df[df["pos_gamma"]]),
        ("negative-gamma (should REPEL)", df[~df["pos_gamma"]]),
        ("ALL days", df),
    ]:
        p = sub["pull"].dropna()
        if len(p) == 0:
            continue
        print(f"  {lbl:30} mean {p.mean() * 100:+.3f}% | toward-wall {100 * (p > 0).mean():.0f}% | n={len(p)}")


def main() -> int:
    walls = get_walls()
    es = es_close_et()
    print(f"walls {len(walls)} days; ES 1m bars {len(es):,} ({es.index.min().date()}..{es.index.max().date()})")
    dist = (np.abs(walls["spot"] - walls["wall"]) / walls["spot"]).mean()
    print(f"avg spot->wall distance: {100 * dist:.2f}% of spot")

    report("FULL DAY 09:30->16:00 (sanity tie-out vs intraday_pin.py)", pulls(es, walls, (9, 30), (16, 0)))
    report("CONTROL 10:00->11:00 (should be ~flat)", pulls(es, walls, (10, 0), (11, 0)))
    report("FINAL HOUR 15:00->16:00 (the 0DTE pin window)", pulls(es, walls, (15, 0), (16, 0)))

    print(
        "\nVERDICT RULE: intraday 0DTE pinning is REAL only if the FINAL HOUR pulls to the wall on "
        "positive-gamma days\n(>55% toward, clearly +), BEATS the control hour, and beats negative-gamma. "
        "Flat/equal/backwards\n-> the minute-OPRA buy stays unjustified; gamma is a grey tile for good."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
