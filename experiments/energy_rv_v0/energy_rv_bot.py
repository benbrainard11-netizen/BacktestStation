"""Energy RV bot v0 -- the one edge that survived every honest test, as a runnable bot.

Cointegration-selected energy spreads (crude/brent/products) mean-revert: confirmed OOS
Sharpe +0.9 on clean daily returns, market-neutral, positive across years (xsectional_rv_v0,
edge_hunt_v0/energy_rv_book.py). This turns that book into an executable daily-rebalanced bot.

HONEST DATA SPLIT (see DATA_NOTE below):
  - signals + PnL come from sync_regime_v0/out/daily_returns.parquet -- the VALIDATED input.
  - price LEVELS for contract sizing come from read_bars daily closes (aligned by date).
  A fresh read_bars resample("1D").last() has a UTC-day-boundary bug on ~30 roll/crash days
  (e.g. it shows CL +3.8% on the 2021-11-29 Omicron crash vs the true ~-9%), which understates
  vol and flips the CL/BZ spread sign. So it is NOT used for signal/PnL, only for sizing levels.

Reports the book at several ACCOUNT SIZES so the integer-contract granularity drag is explicit:
energy CME contracts are $70-100k notional each, so a small account holds ~0 of them at a 12%
vol target -- the book is real but needs size (or micros) to trade.

Run: backend/.venv/Scripts/python.exe experiments/energy_rv_v0/energy_rv_bot.py
"""
from __future__ import annotations

import datetime as dt
import itertools
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, "backend")
from app.data.reader import read_bars  # noqa: E402

OUT = Path(__file__).resolve().parent / "out"
OUT.mkdir(parents=True, exist_ok=True)
RETURNS = Path("experiments/sync_regime_v0/out/daily_returns.parquet")
LEVELS_CACHE = OUT / "energy_daily_closes.parquet"

# CME contract specs: point value ($ per 1.00 move = multiplier) and tick size.
SPECS = {
    "CL.c.0": dict(pv=1000.0, tick=0.01),     # WTI crude, 1000 bbl
    "BZ.c.0": dict(pv=1000.0, tick=0.01),     # Brent, 1000 bbl
    "HO.c.0": dict(pv=42000.0, tick=0.0001),  # ULSD heating oil, 42000 gal
    "RB.c.0": dict(pv=42000.0, tick=0.0001),  # RBOB gasoline, 42000 gal
}
LEGS = list(SPECS)
PAIRS = [p for p in itertools.combinations(LEGS, 2) if set(p) != {"HO.c.0", "RB.c.0"}]  # HO/RB broken

BETAWIN, ZWIN = 250, 60
SPLIT = pd.Timestamp("2023-01-01", tz="UTC")
ANN = np.sqrt(252.0)
VTGT = 0.12
MAXLEV = 12.0
COMM, SLIP_TK = 3.5, 1.0          # $/contract/side, slippage ticks/contract/side
ACCT_SIZES = [30_000, 75_000, 150_000, 300_000, 1_000_000]


def load_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Returns (R, P): validated daily returns + aligned price levels for the energy legs."""
    R = pd.read_parquet(RETURNS)[LEGS]
    R.index = pd.to_datetime(R.index)
    if LEVELS_CACHE.exists():
        P = pd.read_parquet(LEVELS_CACHE)
    else:
        cols = {}
        for s in LEGS:
            df = read_bars(symbol=s, timeframe="1m", start=dt.date(2018, 1, 1), end=dt.date(2026, 5, 30))
            ts = pd.to_datetime(df["ts_event"], utc=True)
            px = df.assign(_ts=ts).set_index("_ts")["close"].resample("1D").last()
            cols[s] = px[px.index.weekday < 5]
        P = pd.DataFrame(cols).ffill(limit=3)
        P.to_parquet(LEVELS_CACHE)
    P.index = pd.to_datetime(P.index)
    P = P.reindex(R.index).ffill().bfill()    # levels for sizing only
    return R.dropna(how="all"), P


def leg_exposures(R: pd.DataFrame, pairs: list[tuple[str, str]]) -> pd.DataFrame:
    """Net per-leg unit exposure e[s,t] from the equal-weight pair book (signals on validated R)."""
    logp = R.cumsum()
    e = pd.DataFrame(0.0, index=R.index, columns=LEGS)
    for a, b in pairs:
        beta = logp[a].rolling(BETAWIN).cov(logp[b]) / logp[b].rolling(BETAWIN).var()
        spread = logp[a] - beta * logp[b]
        z = (spread - spread.rolling(ZWIN).mean()) / spread.rolling(ZWIN).std()
        u = -(z / 2.0).clip(-1.0, 1.0)
        e[a] = e[a].add(u, fill_value=0.0)
        e[b] = e[b].add(-beta * u, fill_value=0.0)
    return e / len(pairs)


def size_book(e: pd.DataFrame, R: pd.DataFrame, P: pd.DataFrame, cap: float):
    """Vol-target to `cap`, return (continuous $pnl, integer $pnl, contracts, diag)."""
    pv = pd.Series({s: SPECS[s]["pv"] for s in LEGS})
    upnl = (e.shift(1) * R).sum(axis=1)
    sig = upnl.rolling(ZWIN).std().shift(1)
    gross_unit = e.abs().sum(axis=1).replace(0, np.nan)
    N = (cap * VTGT / ANN / sig).clip(upper=MAXLEV * cap / gross_unit)
    N = N.replace([np.inf, -np.inf], np.nan).ffill().fillna(0.0)

    dollar_exp = e.mul(N, axis=0)
    contracts = (dollar_exp / (P * pv)).round()
    cont_pnl = (dollar_exp.shift(1) * R).sum(axis=1) - dollar_exp.diff().abs().sum(axis=1) * 4.0 / 1e4
    int_pnl_g = (contracts.shift(1) * (P.shift(1) * pv) * R).sum(axis=1)
    tick_cost = pd.Series({s: COMM + SLIP_TK * SPECS[s]["tick"] * SPECS[s]["pv"] for s in LEGS})
    int_cost = (contracts.diff().abs() * tick_cost).sum(axis=1)
    diag = dict(gross=dollar_exp.abs().sum(axis=1).mean(),
                ncontracts=contracts.abs().sum(axis=1).mean(),
                turn=contracts.diff().abs().sum(axis=1).mean())
    return cont_pnl, int_pnl_g - int_cost, contracts, diag


def stats(pnl: pd.Series, cap: float) -> dict:
    r = (pnl / cap).dropna()
    if len(r) < 50 or r.std() == 0:
        return dict(sh=np.nan, cagr=np.nan, dd=np.nan)
    eq = r.cumsum()
    return dict(sh=float(r.mean() / r.std() * ANN), cagr=float(r.mean() * 252),
                dd=float((eq - eq.cummax()).min()))


def main() -> int:
    R, P = load_data()
    print(f"energy returns: {len(R)} days  {R.index.min().date()}..{R.index.max().date()}  legs={LEGS}")
    print(f"book = {len(PAIRS)} pairs (HO/RB dropped) | vol target {VTGT:.0%} | OOS split {SPLIT.date()}\n")

    for nm, pairs in [("FULL ENERGY BOOK", PAIRS), ("CL/BZ ONLY (the star)", [("CL.c.0", "BZ.c.0")])]:
        e = leg_exposures(R, pairs)
        cont, _, _, _ = size_book(e, R, P, ACCT_SIZES[0])
        cf, co = stats(cont, ACCT_SIZES[0]), stats(cont[cont.index >= SPLIT], ACCT_SIZES[0])
        print(f"=== {nm} ===  continuous: full Sh {cf['sh']:+.2f} | OOS Sh {co['sh']:+.2f} | "
              f"CAGR {cf['cagr']:+.1%} | maxDD {cf['dd']:.1%}")
        print(f"  {'account':>10}  {'int full Sh':>11}  {'int OOS Sh':>10}  {'avg ctrcts':>10}  {'gross/cap':>9}")
        for cap in ACCT_SIZES:
            _, ipnl, _, dg = size_book(e, R, P, cap)
            f, o = stats(ipnl, cap), stats(ipnl[ipnl.index >= SPLIT], cap)
            print(f"  ${cap:>9,.0f}  {f['sh']:>+11.2f}  {o['sh']:>+10.2f}  {dg['ncontracts']:>10.1f}  "
                  f"{dg['gross']/cap:>8.1f}x")
        print()

    # persist deployable artifact at a viable account size (where integer ~ tracks continuous)
    e = leg_exposures(R, PAIRS)
    _, ipnl, contracts, _ = size_book(e, R, P, 150_000)
    out = contracts.add_prefix("pos_")
    out["pnl_int"] = ipnl
    out["equity_int"] = ipnl.cumsum() + 150_000
    out.to_parquet(OUT / "energy_rv_positions.parquet")
    last = contracts.dropna().iloc[-1]
    print(f"wrote {OUT/'energy_rv_positions.parquet'} ($150k acct)")
    print("latest target contracts ($150k): " + ", ".join(f"{s[:-4]}:{int(v):+d}" for s, v in last.items()))
    print("\nDATA_NOTE: signals/PnL use validated daily_returns.parquet; read_bars resample('1D').last() "
          "mis-prints ~30 roll/crash days -> data-quality follow-up before it can be the signal source.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
