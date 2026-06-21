"""Milkability sim for Mira's locked reclaim trades (read-only on the export).

Replays the 305 locked model_reclaim_2r trades through funded Topstep accounts
with staggered start dates, sweeping $-per-R sizing. Answers: started at a random
time, how many accounts survive the trailing DD and reach payout vs blow up?

Honest intraday DD: the exported mae_R is an UNBOUNDED quote-path excursion
(median ~2R, max 63R), not the position's drawdown — the 1R stop caps real
intraday loss. So we cap per-trade adverse at STOP_CAP_R for the breach check.

Reuses sizing_v1/account.py (the funded-account state machine). Output only;
touches nothing in the Mira worktree.
"""
from __future__ import annotations

import datetime as dt
import glob
import sys
from pathlib import Path

import pandas as pd

EXPERIMENT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(EXPERIMENT_DIR))
from account import Account, Trade
from firm_rules import load_firm_config

TRADE_GLOB = r"C:/Users/benbr/bs-mira-v15/**/mira_v15_model_reclaim_2r_trade_list_stressed.parquet"
FIRM_CFG = EXPERIMENT_DIR / "config" / "firms" / "topstep_50k.yaml"

STOP_CAP_R = 1.5          # cap intraday adverse at the stop (position can't lose more)
R_GRID = [50, 75, 100, 150, 200]
N_ACCOUNTS = 100
STAGGER_FRACTION = 0.6    # spread starts across the first 60% of the window


def staggered_starts(dates: list[dt.date], n: int, frac: float) -> list[dt.date]:
    first, last = min(dates), max(dates)
    span = (last - first).days
    horizon = int(round(span * frac))
    if horizon <= 0:
        return [first] * n
    return [first + dt.timedelta(days=int(round(horizon * i / max(1, n - 1)))) for i in range(n)]


def summarize(results: list[dict]) -> dict:
    df = pd.DataFrame(results)
    n = len(df)
    if n == 0:
        return {}
    nb_daily = int((df.status == "blown_daily").sum())
    nb_dd = int((df.status == "blown_dd").sum())
    return {
        "n": n,
        "survive_pct": round(100 * (df.status == "completed").mean(), 1),
        "blown_pct": round(100 * (nb_daily + nb_dd) / n, 1),
        "blown_daily": nb_daily,
        "blown_dd": nb_dd,
        "payout_pct": round(100 * (df.n_payouts > 0).mean(), 1),
        "mean_collected": round(float(df.total_collected.mean()), 0),
        "median_collected": round(float(df.total_collected.median()), 0),
        "best": round(float(df.total_collected.max()), 0),
        "worst": round(float(df.total_collected.min()), 0),
        "mean_trades": round(float(df.n_trades.mean()), 1),
    }


def replay(sub: pd.DataFrame, firm, r_dollars: float, start: dt.date, end: dt.date, acct_id: str) -> dict:
    acc = Account(account_id=acct_id, firm=firm, sim_start_date=start)
    last_d = start
    for r in sub.itertuples(index=False):
        if acc.status != "active":
            break
        pnl = float(r.realized_R_net) * r_dollars
        tr = Trade(
            trade_id="t", entry_ts=r.entry_ts.to_pydatetime(), exit_ts=r.exit_ts.to_pydatetime(),
            symbol=str(r.symbol), direction=int(r.direction), contracts=1,
            entry_price=float(r.entry_px), exit_price=float(r.target_px), pnl_usd=pnl,
            pnl_reason=str(r.exit_reason),
        )
        bal_before = acc.balance
        acc.on_trade_close(tr)
        last_d = r.exit_ts.date()
        if acc.status != "active":
            break
        # Honest intraday breach: worst point during the trade, adverse capped at the stop.
        adverse = min(float(r.mae_R), STOP_CAP_R) * r_dollars
        intraday_low = bal_before - adverse
        if intraday_low < acc.trailing_dd_floor:
            acc.status, acc.blown_reason = "blown_dd", "intraday_mae_trailing_dd"
            break
        if (intraday_low - acc.day_start_balance) <= -firm.daily_loss_limit:
            acc.status, acc.blown_reason = "blown_daily", "intraday_mae_daily"
            break
    acc.finalize(last_d)
    return {
        "account_id": acct_id, "status": acc.status,
        "total_collected": round(acc.total_pnl_collected, 2),
        "n_payouts": len(acc.payouts), "n_trades": len(acc.trades),
    }


def main() -> int:
    path = glob.glob(TRADE_GLOB, recursive=True)[0]
    df = pd.read_parquet(path)
    df["entry_date"] = df["entry_ts"].dt.date
    firm = load_firm_config(FIRM_CFG)
    data_end = max(df["entry_date"]) + dt.timedelta(days=1)

    filters = {
        "all": df,
        "no_ym": df[df.no_ym],
        "no_ym_fav_level": df[df.no_ym & df.fav_level],
        "no_ym_daily_inside": df[df.no_ym & df.daily_inside],
    }

    print(f"Trades: {len(df)} | firm: Topstep $50k (DD ${firm.trailing_drawdown:.0f}, "
          f"daily ${firm.daily_loss_limit:.0f}, target ${firm.payout_profit_threshold:.0f})")
    print(f"{'filter':20s} {'n_trades':>8s}  {'$/R':>5s}  {'survive%':>8s} {'payout%':>8s} "
          f"{'mean$':>9s} {'median$':>9s} {'meanTr':>7s}")
    rows = []
    for fname, fdf in filters.items():
        starts = staggered_starts(sorted(set(fdf["entry_date"])), N_ACCOUNTS, STAGGER_FRACTION)
        fdf = fdf.sort_values("entry_ts")
        for rd in R_GRID:
            results = []
            for i, s in enumerate(starts):
                sub = fdf[(fdf["entry_date"] >= s) & (fdf["entry_date"] < data_end)]
                if len(sub) == 0:
                    continue
                results.append(replay(sub, firm, rd, s, data_end, f"{fname}_{rd}_{i:03d}"))
            s = summarize(results)
            s.update(filter=fname, n_trades=len(fdf), r_dollars=rd)
            rows.append(s)
            print(f"{fname:20s} {len(fdf):>8d}  {rd:>5d}  {s['survive_pct']:>7.1f}% "
                  f"{s['payout_pct']:>7.1f}% {s['mean_collected']:>9.0f} {s['median_collected']:>9.0f} "
                  f"{s['mean_trades']:>7.1f}")
    out = EXPERIMENT_DIR / "out" / "mira_reclaim_milkability.parquet"
    out.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_parquet(out, index=False)
    print(f"\nWrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
