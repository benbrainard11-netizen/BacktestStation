"""Assemble the raw intraday option quotes (§6) + band OI (§7) into model-ready per-(root,date) panels.

Per Ben's scope: guard the quotes + underlying; BS-invert IV from the mid and recompute greeks
ourselves; pair PRIOR-day OI (leak-clean); store queryable by (root, date) — not hash-keyed shards.

Pipeline per root:
  Stage 1 (enrich, per expiration, threaded):
    - read all per-contract quote files for the exp, mid = (bid+ask)/2 where both > 0
    - underlying S(t) = fut(t) + basis(D-1)  -- FULLY CAUSAL. fut(t) is the index future at minute t
      (merge_asof nearest prior minute). basis(D-1) is the PRIOR trading day's (parity-forward - futures-
      close), from the validated daily walls; the basis is stable day-to-day, so this is both leak-free
      and basis-correct (no whole-day anchor peeking into the future). Falls back to S=fut(t) where no
      prior-day basis exists. `moneyness` = strike/S - 1 lets you causally subset the ±band at use-time.
    - intraday T to a 16:00 ET expiry; IV via build_walls_ndx.implied_vol; gamma/vanna/charm
      (option_greeks, finite-difference verified). IV is set NaN when it is unreliable: bracket-pinned
      (no solution / saturated to 500%), unidentifiable (vega below a floor, e.g. deep ITM near
      intrinsic), or within T_MIN of expiry; greeks are NaN (NOT 0.0) wherever IV is NaN.
    - oi_prior: OI from the PRIOR *trading* day (calendar built from RTH sessions, not the 24h futures
      clock — otherwise Friday OI maps onto a Sunday Globex date and every Monday loses its OI)
    -> out/panel_byexp/root=R/exp=E.parquet  (fixed OUT_COLS schema on every file)
  Stage 2 (repartition): stream byexp -> out/panel/root=R/date=YYYYMMDD/  (hive, (root,date)-queryable)

LEAK-FREE BY CONSTRUCTION: every column at minute t uses only data known by t -- quotes/fut are
point-in-time, basis is prior-day, oi_prior is prior-trading-day, T/dte are known in advance. AND row
EXISTENCE is causal: the build drops any row with |moneyness| > PANEL_BAND (moneyness vs the causal
underlying(t)), so the set of strikes present at minute t depends only on current-minute spot -- not on
the pull's full-life band. Nothing in-band is lost (the pulled band is a superset). So the on-disk panel
is fully causal; no use-time masking required.

Run:  python build_option_panels.py NDXP            # full root
      python build_option_panels.py NDXP --sample 20250703   # one date (validation, no repartition)
The greeks self-check runs first; the build aborts if it fails.
"""

from __future__ import annotations

import glob
import os
import shutil
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.dataset as ds

sys.path.insert(0, str(Path(__file__).resolve().parent))
import option_greeks as G  # noqa: E402
from build_walls_ndx import implied_vol  # noqa: E402
from gex_pull import _ymd  # noqa: E402

HERE = Path(__file__).resolve().parent
QUOTES = HERE / "out" / "intraday_pc"
OI = HERE / "out" / "intraday_oi"
# byexp intermediate + final panels can be relocated off C: via PANEL_BASE (e.g. D:\data\processed\option_panels)
_PB = Path(os.environ.get("PANEL_BASE", str(HERE / "out")))
BYEXP = _PB / "panel_byexp"
PANEL = _PB / "panel"
BARS = Path(r"D:\data\processed\bars\timeframe=1m")
FUT = {
    "NDXP": ("NQ.c.0", 1.0),
    "SPXW": ("ES.c.0", 1.0),
    "RUTW": ("RTY.c.0", 1.0),
    "DJX": ("YM.c.0", 0.01),
    "NDX": ("NQ.c.0", 1.0),
    "SPX": ("ES.c.0", 1.0),
    "RUT": ("RTY.c.0", 1.0),
}  # monthly/deep-history roots
YEAR_SEC = 365.25 * 86400.0
RTH_LO, RTH_HI = 34200000, 57600000  # 09:30, 16:00 ET in ms-of-day (real option session)
T_MIN = 600.0 / YEAR_SEC  # < 10 min to expiry -> greeks unreliable (charm blows up)
IV_LO, IV_HI = 1e-3, 5.0  # implied_vol() bisection bracket; pinned => no solution
VEGA_FLOOR_REL = 1e-4  # vega < this * S => IV not identifiable (deep ITM/OTM)
ASOF_TOL_MS = 30 * 60000  # futures asof: don't reach back > 30 min for a price
PANEL_BAND = float(
    os.environ.get("PANEL_BAND", "0.07")
)  # keep only |moneyness| <= this (causal band, on disk)
OUT_COLS = [
    "date",
    "ms_of_day",
    "expiration",
    "strike",
    "right",
    "bid",
    "ask",
    "bid_size",
    "ask_size",
    "mid",
    "underlying_price",
    "fut_price",
    "basis",
    "moneyness",
    "dte",
    "implied_vol",
    "gamma",
    "vanna",
    "charm",
    "oi_prior",
]
# daily walls supply the validated per-day parity forward used for the (prior-day) basis
_WALLS = {
    "NDX": HERE.parent / "fuhhhhh" / "out" / "walls_ndx.parquet",
    "SPX": HERE.parent / "fuhhhhh" / "out" / "walls_v2.parquet",
    "RUT": HERE / "out" / "walls_rut.parquet",
    "DJX": HERE / "out" / "walls_djx.parquet",
}
_INDEX = {"NDX": "NDX", "NDXP": "NDX", "SPX": "SPX", "SPXW": "SPX", "RUT": "RUT", "RUTW": "RUT", "DJX": "DJX"}

_FUT_DF: pd.DataFrame | None = None  # (date, ms_of_day) -> fut close, ET clock; loaded per root
_BASIS: dict[int, float] = {}  # date -> PRIOR-day basis (forward - fut close); causal


def load_futures(root: str) -> pd.DataFrame:
    """Index future 1m closes on the ET clock, keyed (date, ms_of_day) to match option quotes."""
    sym, scale = FUT[root]
    d = (
        ds.dataset(BARS / f"symbol={sym}", format="parquet")
        .to_table(columns=["ts_event", "close"])
        .to_pandas()
    )
    ts = pd.to_datetime(d["ts_event"], utc=True).dt.tz_convert("America/New_York")
    out = pd.DataFrame(
        {
            "date": ts.dt.strftime("%Y%m%d").astype(int),
            "ms_of_day": ((ts.dt.hour * 3600 + ts.dt.minute * 60 + ts.dt.second) * 1000).astype(int),
            "fut": d["close"].to_numpy(float) * scale,
        }
    )
    return (
        out.drop_duplicates(["date", "ms_of_day"]).sort_values(["date", "ms_of_day"]).reset_index(drop=True)
    )


def rth_trading_dates(fut: pd.DataFrame) -> np.ndarray:
    """Real (RTH) trading dates — excludes Sunday-evening-only Globex dates that break the OI calendar."""
    rth = fut[(fut["ms_of_day"] >= RTH_LO) & (fut["ms_of_day"] <= RTH_HI)]
    return np.array(sorted(int(x) for x in rth["date"].unique()))


def next_trading_day_map(dates: np.ndarray) -> dict[int, int]:
    """date -> the NEXT trading date present (prior-day OI: OI(D) is first usable on map[D])."""
    u = np.array(sorted(set(int(x) for x in dates)))
    return {int(u[i]): int(u[i + 1]) for i in range(len(u) - 1)}


def daily_basis(root: str, fut: pd.DataFrame) -> dict[int, float]:
    """date -> PRIOR-trading-day basis (parity_forward - futures_close), so the underlying is causal.

    basis(D) = walls.spot(D) - futures_close(D) (spot = the validated daily parity forward). We then
    reindex to the trading calendar, forward-fill gaps, and SHIFT +1 day, so day D applies basis(D-1)
    — known before D opens. Returns {} if the walls file is missing (caller falls back to S = fut)."""
    wf = _WALLS.get(_INDEX.get(root, root))
    if wf is None or not wf.exists():
        return {}
    tdates = rth_trading_dates(fut)
    rth = fut[(fut["ms_of_day"] >= RTH_LO) & (fut["ms_of_day"] <= RTH_HI)]
    fut_close = rth.sort_values("ms_of_day").groupby("date")["fut"].last()
    spot = pd.read_parquet(wf)[["date", "spot"]].astype({"date": int}).set_index("date")["spot"]
    basis = (spot - fut_close).dropna()
    causal = basis.reindex(tdates).ffill().shift(1)  # apply PRIOR day's basis -> leak-free
    return {int(d): float(v) for d, v in causal.items() if np.isfinite(v)}


def _read_quotes(files: list[str]) -> tuple[pd.DataFrame | None, int]:
    """Read per-contract files one at a time so a single corrupt file can't abort the whole root."""
    parts, bad = [], 0
    for f in files:
        try:
            parts.append(pd.read_parquet(f))
        except Exception:
            bad += 1
    return (pd.concat(parts, ignore_index=True) if parts else None), bad


def _add_underlying(q: pd.DataFrame) -> pd.DataFrame:
    # merge_asof requires both frames sorted by the `on` key (ms_of_day) globally; `by` partitions on date
    q = q.sort_values("ms_of_day")
    fut = _FUT_DF.sort_values("ms_of_day")
    q = pd.merge_asof(q, fut, on="ms_of_day", by="date", direction="backward", tolerance=ASOF_TOL_MS)
    futt = q["fut"].to_numpy(float)
    basis = q["date"].map(_BASIS).to_numpy(float)  # PRIOR-day basis (causal); NaN if none
    S = futt + np.where(np.isfinite(basis), basis, 0.0)  # causal underlying = fut(t) + basis(D-1)
    S = np.where(np.isfinite(S), S, np.nan)
    q["fut_price"], q["basis"], q["underlying_price"] = futt, basis, S
    with np.errstate(all="ignore"):
        q["moneyness"] = q["strike"].to_numpy(float) / S - 1.0  # causal band filter: |moneyness| <= 0.07
    return q


def _add_greeks(q: pd.DataFrame, exp: int) -> pd.DataFrame:
    qdt = pd.to_datetime(q["date"].astype(int).astype(str), format="%Y%m%d") + pd.to_timedelta(
        q["ms_of_day"], "ms"
    )
    edt = pd.to_datetime(str(int(exp)), format="%Y%m%d") + pd.Timedelta(hours=16)
    T = ((edt - qdt).dt.total_seconds() / YEAR_SEC).to_numpy(float)
    q["dte"] = (pd.to_datetime(str(int(exp)), format="%Y%m%d") - qdt.dt.normalize()).dt.days
    S, K = q["underlying_price"].to_numpy(float), q["strike"].to_numpy(float)
    is_call = q["right"].to_numpy() == "C"
    iv = np.full(len(q), np.nan)
    ok = np.isfinite(S) & (T > T_MIN)  # skip near-expiry + missing-underlying rows
    iv[ok] = implied_vol(q["mid"].to_numpy(float)[ok], S[ok], K[ok], T[ok], is_call[ok])
    pinned = (iv <= IV_LO + 1e-9) | (iv >= IV_HI - 1e-9)  # no solution / saturated to 500%
    vega = G.bs_vega(S, K, np.where(ok, T, np.nan), iv)
    weak = ~np.isfinite(vega) | (vega < VEGA_FLOOR_REL * np.where(np.isfinite(S), S, 0.0))  # unidentifiable
    iv = np.where(pinned | weak, np.nan, iv)
    good = np.isfinite(iv)
    q["implied_vol"] = iv
    Tg = np.maximum(T, 1e-9)
    for name, fn in (("gamma", G.bs_gamma), ("vanna", G.bs_vanna), ("charm", G.bs_charm)):
        q[name] = np.where(good, fn(S, K, Tg, iv), np.nan)  # NaN (not 0.0) where IV unreliable
    return q


def _attach_oi(q: pd.DataFrame, root: str, exp: int, oi_next: dict[int, int]) -> pd.DataFrame:
    oif = OI / f"root={root}" / f"exp={exp}.parquet"
    if not oif.exists():
        q["oi_prior"] = np.nan
        return q
    oi = pd.read_parquet(oif)[["date", "strike", "right", "open_interest"]].copy()
    oi["right"] = oi["right"].astype(str).str.upper().str[0]
    oi["date"] = oi["date"].astype(int).map(oi_next)  # shift to the day it's first usable
    oi = oi.dropna(subset=["date"])
    oi["date"] = oi["date"].astype(int)
    return q.merge(
        oi.rename(columns={"open_interest": "oi_prior"}), on=["date", "strike", "right"], how="left"
    )


def _stats(q: pd.DataFrame) -> dict:
    dow = pd.to_datetime(q["date"].astype(int).astype(str), format="%Y%m%d").dt.dayofweek
    mon = dow == 0
    return {
        "wrote": 1,
        "rows": len(q),
        "und": int(q["underlying_price"].notna().sum()),
        "iv": int(q["implied_vol"].notna().sum()),
        "gam": int(q["gamma"].notna().sum()),
        "oi": int(q["oi_prior"].notna().sum()),
        "mon_rows": int(mon.sum()),
        "mon_oi": int(q.loc[mon, "oi_prior"].notna().sum()),
    }


_ZERO = {"wrote": 0, "rows": 0, "und": 0, "iv": 0, "gam": 0, "oi": 0, "mon_rows": 0, "mon_oi": 0}


def enrich_exp(root: str, exp: int, oi_next: dict[int, int]) -> dict:
    outf = BYEXP / f"root={root}" / f"exp={exp}.parquet"
    if outf.exists():
        return dict(_ZERO)
    files = glob.glob(str(QUOTES / f"root={root}" / f"exp={exp}" / "*.parquet"))
    if not files:
        return dict(_ZERO)
    q, _bad = _read_quotes(files)
    if q is None:
        return dict(_ZERO)
    q["right"] = q["right"].astype(str).str.upper().str[0]
    bid, ask = q["bid"].to_numpy(float), q["ask"].to_numpy(float)
    q = q[(bid > 0) & (ask > 0)].copy()
    if q.empty:
        return dict(_ZERO)
    q["mid"] = 0.5 * (q["bid"].to_numpy(float) + q["ask"].to_numpy(float))
    q = _add_underlying(q)
    # ENFORCE the causal band on disk: keep only strikes within ±PANEL_BAND of the CURRENT-minute
    # underlying. Row existence then depends only on underlying(t) (causal) — kills the strike-universe
    # leak where the pulled full-life band let a strike's mere presence encode future spot. Also drops
    # rows with no underlying (NaN moneyness). The pulled band is a superset, so nothing in-band is lost.
    q = q[q["moneyness"].abs() <= PANEL_BAND].copy()
    if q.empty:
        return dict(_ZERO)
    q = _add_greeks(q, exp)
    q = _attach_oi(q, root, exp, oi_next)
    q = q.reindex(columns=OUT_COLS)  # identical schema on every exp file
    st = _stats(q)
    outf.parent.mkdir(parents=True, exist_ok=True)
    tmp = outf.with_suffix(".tmp.parquet")
    q.sort_values(["date", "ms_of_day", "strike", "right"]).to_parquet(tmp)
    tmp.replace(outf)
    return st


def repartition(root: str) -> None:
    src, dst = BYEXP / f"root={root}", PANEL / f"root={root}"
    if not src.exists():
        print(f"[{root}] no byexp output — nothing to repartition", flush=True)
        return
    dset = ds.dataset(str(src), format="parquet")
    if dset.count_rows() == 0:
        print(f"[{root}] byexp has 0 rows — empty panel skipped", flush=True)
        return
    if dst.exists():
        shutil.rmtree(dst, ignore_errors=True)  # full rebuild: drop stale date partitions
    dst.mkdir(parents=True, exist_ok=True)
    ds.write_dataset(
        dset,
        base_dir=str(dst),
        format="parquet",
        partitioning=ds.partitioning(pa.schema([("date", pa.int64())]), flavor="hive"),
        existing_data_behavior="delete_matching",
    )
    print(f"[{root}] repartitioned {dset.count_rows()} rows -> {dst} (per date)", flush=True)


def main() -> int:
    G.selfcheck(verbose=False)  # abort if greeks are wrong
    root = sys.argv[1]
    sample = sys.argv[sys.argv.index("--sample") + 1] if "--sample" in sys.argv else None
    global _FUT_DF, _BASIS
    _FUT_DF = load_futures(root)
    _BASIS = daily_basis(root, _FUT_DF)  # prior-day basis -> causal underlying
    print(
        f"[{root}] causal basis: {len(_BASIS)} trading days" + ("" if _BASIS else " (no walls -> S=fut)"),
        flush=True,
    )
    oi_next = next_trading_day_map(rth_trading_dates(_FUT_DF))  # RTH calendar (no Sunday Globex dates)
    exps = sorted(int(Path(p).name.split("=")[1]) for p in glob.glob(str(QUOTES / f"root={root}" / "exp=*")))
    if sample:
        sd = int(sample)
        exps = [E for E in exps if sd <= E and sd >= int(_ymd(pd.Timestamp(str(E)) - pd.Timedelta(days=60)))]
        print(f"[{root}] SAMPLE {sd}: {len(exps)} candidate exps")
    print(f"[{root}] {len(exps)} expirations -> enrich", flush=True)
    agg = dict(_ZERO)
    with ThreadPoolExecutor(max_workers=int(os.environ.get("WORKERS", "6"))) as pool:
        for i, st in enumerate(pool.map(lambda E: enrich_exp(root, E, oi_next), exps)):
            for k in agg:
                agg[k] += st[k]
            if (i + 1) % 50 == 0:
                print(f"  ...{i+1}/{len(exps)} exps, {agg['wrote']} written", flush=True)
    if agg["rows"]:
        r = agg
        print(
            f"[{root}] enriched {r['wrote']} exps, {r['rows']:,} rows | coverage: "
            f"underlying {100*r['und']/r['rows']:.1f}% iv {100*r['iv']/r['rows']:.1f}% "
            f"gamma {100*r['gam']/r['rows']:.1f}% oi_prior {100*r['oi']/r['rows']:.1f}%",
            flush=True,
        )
        if r["mon_rows"]:
            print(
                f"[{root}] Monday oi_prior non-null {100*r['mon_oi']/r['mon_rows']:.1f}% "
                f"(calendar-fix check: should be >0)",
                flush=True,
            )
    else:
        print(f"[{root}] enriched 0 new exps (all present or empty)", flush=True)
    if not sample:
        repartition(root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
