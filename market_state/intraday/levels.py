"""Level engine: the objective zone set per trading day, no-lookahead, from 1m bars (ET-segmented).

Per trading day D, the touchable levels (each known by the time a touch could occur):
  pdh / pdl   prior RTH session high / low
  pdc         prior RTH close            (daily + RTH gap-fill magnet)
  rth_open    today's RTH open           (the other gap edge; known 09:30)
  onh / onl   overnight high / low       (prev 18:00 ET -> today 09:30 ET)
  orh / orl   opening-range high / low   (today 09:30-09:45 ET; valid only AFTER 09:45)
  pwc         prior-week Friday close     (weekly gap-fill)
Round numbers + VWAP + VPOC come later (round = touch-time/confluence; VWAP/VPOC are dynamic/heavier).

Run (smoke): backend/.venv/Scripts/python.exe market_state/intraday/levels.py
"""
from __future__ import annotations

import sys

import pandas as pd

sys.path.insert(0, "backend")
from app.data.reader import read_bars  # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ET = "America/New_York"
SYM = "ES.c.0"
START, END = "2025-04-01", "2026-06-01"
RTH_O, RTH_C, OR_END, ON_START = 570, 960, 585, 1080  # ET minutes since midnight (09:30,16:00,09:45,18:00)


def load_1m_et() -> pd.DataFrame:
    b = read_bars(symbol=SYM, timeframe="1m", start=START, end=END)
    ts = pd.to_datetime(b["ts_event"], utc=True).dt.tz_convert(ET)
    df = pd.DataFrame({"o": b["open"].to_numpy(), "h": b["high"].to_numpy(),
                       "l": b["low"].to_numpy(), "c": b["close"].to_numpy()}, index=ts).sort_index()
    df["date"] = df.index.normalize()
    df["tod"] = df.index.hour * 60 + df.index.minute
    return df


def build_levels() -> pd.DataFrame:
    df = load_1m_et()
    rth = df[(df["tod"] >= RTH_O) & (df["tod"] < RTH_C)]
    R = rth.groupby("date").agg(rth_h=("h", "max"), rth_l=("l", "min"),
                                rth_o=("o", "first"), rth_c=("c", "last")).sort_index()
    orr = rth[rth["tod"] < OR_END].groupby("date").agg(or_h=("h", "max"), or_l=("l", "min"))

    # overnight (prev 18:00 ET -> today 09:30 ET): evening bars belong to the NEXT calendar day's session
    on = df[(df["tod"] >= ON_START) | (df["tod"] < RTH_O)].copy()
    on["on_date"] = on["date"]
    eve = on["tod"] >= ON_START
    on.loc[eve, "on_date"] = (on.index[eve] + pd.Timedelta(days=1)).normalize()
    ON = on.groupby("on_date").agg(onh=("h", "max"), onl=("l", "min"))

    # prior-week Friday close (weekly gap-fill)
    iso = R.index.isocalendar()
    R = R.assign(yw=iso["year"].astype(int).astype(str) + "-" + iso["week"].astype(int).astype(str).str.zfill(2))
    wc = R.groupby("yw")["rth_c"].last()
    wprev = {wc.index[i]: float(wc.iloc[i - 1]) for i in range(1, len(wc))}

    out = pd.DataFrame(index=R.index)
    out["pdh"], out["pdl"], out["pdc"] = R["rth_h"].shift(1), R["rth_l"].shift(1), R["rth_c"].shift(1)
    out["rth_open"] = R["rth_o"]                 # known 09:30 (gap edge)
    out["onh"] = ON["onh"].reindex(R.index)
    out["onl"] = ON["onl"].reindex(R.index)
    out["orh"] = orr["or_h"].reindex(R.index)    # valid AFTER 09:45 (enforced by the event detector)
    out["orl"] = orr["or_l"].reindex(R.index)
    out["pwc"] = R["yw"].map(wprev)
    return out


LEVEL_COLS = ["pdh", "pdl", "pdc", "rth_open", "onh", "onl", "orh", "orl", "pwc"]


def main() -> int:
    lv = build_levels()
    print(f"levels for {len(lv)} trading days ({lv.index.min().date()}..{lv.index.max().date()})\n")
    print("last 6 days (sanity: ES ~5000-6500, pdh>pdl, onh>=onl, orh>=orl):")
    print(lv[LEVEL_COLS].tail(6).round(2).to_string())
    bad = int((lv["pdh"] < lv["pdl"]).sum() + (lv["onh"] < lv["onl"]).sum() + (lv["orh"] < lv["orl"]).sum())
    print(f"\nsanity: hi<lo violations = {bad} (must be 0)")
    print("coverage: " + " | ".join(f"{c} {lv[c].notna().mean():.0%}" for c in LEVEL_COLS))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
