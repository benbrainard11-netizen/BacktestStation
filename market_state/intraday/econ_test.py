"""The economics check -- is the level/OFI signal worth MONEY after costs? (held to the same CI bar as everything)

Simulates the honest trade: FADE a line level (bet it holds) at the touch. Win (hold) = +M*ATR; lose (break)
= -M*ATR (symmetric, so LINE levels only -- zones have asymmetric payoffs = the AUC mirage). Day-block
bootstrap CI on E[$] (events cluster by day), at two cost assumptions. OFI filter = fade only when flow isn't
pushing the break. OOS only. ES: 1 pt = $50.

Run: backend/.venv/Scripts/python.exe market_state/intraday/econ_test.py
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

EVENTS = Path("market_state/out/events_v2_ES.parquet")
OOS_START = pd.Timestamp("2026-03-01", tz="UTC")
LINES = ["pdh", "pdl", "onh", "onl", "pwc"]
M, TARGET, PTV, N_BOOT = 0.05, "y05", 50.0, 2000
COSTS = [0.60, 1.00]  # ES pts round-turn: $30 (optimistic limit fade) and $50 (realistic w/ slippage)


def boot_exp(te: pd.DataFrame, cost: float):
    risk = M * te["atr"].to_numpy()
    win = te[TARGET].to_numpy() == 0
    net = np.where(win, risk, -risk) - cost           # +target on hold, -stop on break, honest cost
    days = te["day"].to_numpy()
    uniq = np.unique(days)
    di = {d: np.where(days == d)[0] for d in uniq}
    rng = np.random.default_rng(0)
    boot = [net[np.concatenate([di[d] for d in rng.choice(uniq, len(uniq), replace=True)])].mean()
            for _ in range(N_BOOT)]
    return net.mean(), np.percentile(boot, 5), np.percentile(boot, 95), win.mean()


def report(name: str, te: pd.DataFrame) -> None:
    if len(te) < 30:
        print(f"   {name:18} n={len(te)} (too few)")
        return
    for cost in COSTS:
        m, lo, hi, hold = boot_exp(te, cost)
        flag = "REAL >0" if lo > 0 else ("marginal" if hi > 0 else "NEGATIVE")
        print(f"   {name:18} cost {cost:.1f}pt:  E[$]={m * PTV:+6.1f} [{lo * PTV:+5.0f}, {hi * PTV:+5.0f}]  "
              f"hold%={hold:.2f}  n={len(te)}  -> {flag}")


def main() -> int:
    df = pd.read_parquet(EVENTS)
    df.index = pd.to_datetime(df.index, utc=True)
    df["day"] = df.index.tz_convert("America/New_York").normalize().tz_localize(None)
    df = df[df["level"].isin(LINES)].dropna(subset=[TARGET])
    te = df[df.index >= OOS_START]
    print(f"FADE-the-level economics, OOS (day-block bootstrap CI; target=stop=M*ATR ~{M*df['atr'].mean():.1f}pt):\n")
    report("ALL line levels", te)
    report("ALL + OFI filter", te[te["ofi_signed"] <= 0])
    report("overnight only", te[te["level"].isin(["onh", "onl"])])
    report("overnight + OFI", te[(te["level"].isin(["onh", "onl"])) & (te["ofi_signed"] <= 0)])
    print("\nVERDICT: a config whose CI clears 0 at the REALISTIC ($50) cost = a real (small) edge worth keeping.")
    print("         everything marginal/negative at realistic cost => moves too small to beat costs -> Mira/RV.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
