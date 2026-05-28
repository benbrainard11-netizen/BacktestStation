"""Walk-forward trade simulator for a single funded account.

Drives the model's signal stream through one Account:
  1. Load LightGBM ensemble predictions (active cells from strategy config)
  2. Build a time-ordered signal stream
  3. Event loop: close due positions, then consider new entries
     - One open position per symbol (v1 simplification)
     - risk_manager gates each entry
     - exits are time-based at the signal's horizon
  4. Apply each closed trade to the Account in exit-time order
  5. Finalize

P&L per trade (matches evaluate.py's economic overlay):
  gross_pts = entry_price * (exp(realized_logret) - 1)
  gross_usd = gross_pts * point_value * direction * contracts
  slippage  = 2 ticks * tick_size * point_value * contracts
  commission = 1.50 * contracts
  pnl = gross_usd - slippage - commission

See PLAN.md §6, §7, §8.
"""

from __future__ import annotations

import argparse
import datetime as dt
import heapq
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

THIS_FILE = Path(__file__).resolve()
EXPERIMENT_DIR = THIS_FILE.parent
REPO_ROOT = EXPERIMENT_DIR.parents[1]
sys.path.insert(0, str(EXPERIMENT_DIR))

from account import Account, Trade
from firm_rules import FirmConfig, load_firm_config
import risk_manager

TICK_SIZES = {"ES.c.0": 0.25, "NQ.c.0": 0.25, "YM.c.0": 1.0, "RTY.c.0": 0.10}

# Mini (full-size) vs Micro contract point values.
# Micros are 1/10th the dollar value per point (MES=$5 vs ES=$50, etc).
POINT_VALUES_MINI = {"ES.c.0": 50.0, "NQ.c.0": 20.0, "YM.c.0": 5.0, "RTY.c.0": 50.0}
POINT_VALUES_MICRO = {"ES.c.0": 5.0, "NQ.c.0": 2.0, "YM.c.0": 0.5, "RTY.c.0": 5.0}


def point_values_for(contract_type: str) -> dict[str, float]:
    if contract_type == "micro":
        return POINT_VALUES_MICRO
    if contract_type == "mini":
        return POINT_VALUES_MINI
    raise ValueError(f"unknown contract_type: {contract_type!r}")


def horizon_min_from_key(h_key: str) -> int:
    return int(h_key.replace("h_", "").replace("m", ""))


@dataclass(frozen=True)
class Signal:
    ts_decision: dt.datetime
    symbol: str
    horizon_key: str
    horizon_minutes: int
    threshold: float
    p_flat: float
    p_up: float
    p_down: float
    entry_price: float
    realized_logret: float

    @property
    def p_proba(self) -> np.ndarray:
        return np.array([self.p_flat, self.p_up, self.p_down], dtype=np.float64)


@dataclass
class OpenPosition:
    symbol: str
    horizon_key: str
    signal_ts: pd.Timestamp        # original ts_decision, for excursion lookup
    entry_ts: dt.datetime
    exit_ts: dt.datetime
    direction: int
    contracts: int
    entry_price: float
    realized_logret: float
    trade_id: str


# ---------------------------------------------------------------------------
# Signal loading
# ---------------------------------------------------------------------------


def load_signals(strategy_cfg: dict, predictions_dir: Path) -> list[Signal]:
    """Build the time-ordered signal stream from model predictions + active cells."""
    active_cells = strategy_cfg["active_cells"]
    pred_files = sorted(predictions_dir.glob("fold_*_test.parquet"))
    # Include holdout if present
    holdout = predictions_dir / "fold_holdout_holdout.parquet"
    if holdout.exists():
        pred_files.append(holdout)

    if not pred_files:
        raise FileNotFoundError(f"no prediction files in {predictions_dir}")

    signals: list[Signal] = []
    seen: set[tuple] = set()    # dedup (symbol, horizon, ts) across overlapping folds

    for pq in pred_files:
        df = pd.read_parquet(pq)
        df["ts_decision"] = pd.to_datetime(df["ts_decision"], utc=True)
        for cell in active_cells:
            sym = cell["symbol"]
            hkey = cell["horizon"]
            thr = float(cell["threshold"])
            hmin = horizon_min_from_key(hkey)

            sub = df[df["symbol"] == sym]
            if len(sub) == 0:
                continue
            flat_col, up_col, down_col = f"{hkey}_p_flat", f"{hkey}_p_up", f"{hkey}_p_down"
            ret_col = f"{hkey}_realized_logret"
            if any(c not in sub.columns for c in [flat_col, up_col, down_col, ret_col]):
                continue

            for row in sub.itertuples(index=False):
                ts = getattr(row, "ts_decision")
                realized = getattr(row, ret_col)
                entry = getattr(row, "entry_price")
                if pd.isna(realized) or pd.isna(entry):
                    continue
                key = (sym, hkey, ts)
                if key in seen:
                    continue
                seen.add(key)
                signals.append(Signal(
                    ts_decision=ts.to_pydatetime(),
                    symbol=sym,
                    horizon_key=hkey,
                    horizon_minutes=hmin,
                    threshold=thr,
                    p_flat=float(getattr(row, flat_col)),
                    p_up=float(getattr(row, up_col)),
                    p_down=float(getattr(row, down_col)),
                    entry_price=float(entry),
                    realized_logret=float(realized),
                ))

    signals.sort(key=lambda s: (s.ts_decision, s.symbol, s.horizon_key))
    return signals


def trade_pnl_usd(
    *,
    symbol: str,
    direction: int,
    contracts: int,
    entry_price: float,
    realized_logret: float,
    point_value: float,
    slippage_ticks_per_side: float,
    commission_usd: float,
    stop_loss_usd_per_contract: float | None = None,
    window_max_high: float | None = None,
    window_min_low: float | None = None,
) -> tuple[float, str]:
    """Compute trade P&L. Returns (pnl_usd, exit_reason).

    If a stop is set AND we have excursion data, check whether the adverse
    move hit the stop intra-trade. If so, the trade exits at the stop loss
    (capped downside). Otherwise it exits at the horizon's realized return.
    """
    tick = TICK_SIZES[symbol]
    slippage_usd = (2.0 * slippage_ticks_per_side * tick) * point_value * contracts
    commission = commission_usd * contracts

    # Stop check (uses precomputed excursion)
    if (stop_loss_usd_per_contract is not None
            and window_max_high is not None and window_min_low is not None
            and not np.isnan(window_max_high) and not np.isnan(window_min_low)):
        stop_points = stop_loss_usd_per_contract / point_value
        if direction == 1:   # long: adverse = how far price fell below entry
            adverse_points = entry_price - window_min_low
        else:                # short: adverse = how far price rose above entry
            adverse_points = window_max_high - entry_price
        if adverse_points >= stop_points:
            # Stopped out: lose exactly the stop amount per contract + costs
            pnl = -stop_loss_usd_per_contract * contracts - slippage_usd - commission
            return (float(pnl), "stop")

    # Time-only exit at horizon
    gross_pts = entry_price * (np.exp(realized_logret) - 1.0)
    gross_usd = gross_pts * point_value * direction * contracts
    return (float(gross_usd - slippage_usd - commission), "horizon_exit")


def load_excursions(path: Path) -> dict[tuple[str, str, int], tuple[float, float]]:
    """Load excursions.parquet → {(symbol, horizon_key, ts_ns): (max_high, min_low)}.

    Keyed by int64 UTC nanoseconds to avoid Timestamp equality/tz subtleties.
    """
    if not path.exists():
        return {}
    df = pd.read_parquet(path)
    df["ts_decision"] = pd.to_datetime(df["ts_decision"], utc=True)
    lookup: dict[tuple[str, str, int], tuple[float, float]] = {}
    for row in df.itertuples(index=False):
        lookup[(row.symbol, row.horizon_key, int(pd.Timestamp(row.ts_decision).value))] = (
            row.window_max_high, row.window_min_low,
        )
    return lookup


# ---------------------------------------------------------------------------
# Single-account simulation
# ---------------------------------------------------------------------------


def simulate_account(
    *,
    account: Account,
    signals: list[Signal],
    firm: FirmConfig,
    strategy_cfg: dict,
    jitter_seed: int,
    excursions: dict | None = None,
) -> Account:
    """Run one account through the signal stream. Mutates + returns the account."""
    rng = np.random.default_rng(jitter_seed)
    sizing_method = strategy_cfg.get("sizing_method", "fixed_1")
    sizing_params = strategy_cfg.get("sizing_params", {})
    costs = strategy_cfg.get("costs", {})
    slip = float(costs.get("slippage_ticks_per_side", 1.0))
    comm = float(costs.get("commission_usd", 1.50))
    dir_gap = float(strategy_cfg.get("direction_filter", {}).get("require_max_minus_runner_up", 0.0))

    contract_type = strategy_cfg.get("contract_type", "mini")
    point_values = point_values_for(contract_type)
    exit_cfg = strategy_cfg.get("exit", {})
    stop_usd = exit_cfg.get("stop_loss_usd_per_contract", None)
    stop_usd = float(stop_usd) if stop_usd is not None else None
    excursions = excursions or {}
    # Firm position cap is in mini-equivalents; micros get 10x the count.
    effective_max = firm.max_position_size * (10 if contract_type == "micro" else 1)

    open_symbols: set[str] = set()
    pending_exits: list[tuple] = []   # heap of (exit_ts, seq, OpenPosition)
    seq = 0
    trade_counter = 0
    last_date = account.sim_start_date

    def close_position(pos: OpenPosition) -> None:
        nonlocal trade_counter
        wmax, wmin = excursions.get(
            (pos.symbol, pos.horizon_key, int(pd.Timestamp(pos.signal_ts).value)), (None, None)
        )
        pnl, reason = trade_pnl_usd(
            symbol=pos.symbol, direction=pos.direction, contracts=pos.contracts,
            entry_price=pos.entry_price, realized_logret=pos.realized_logret,
            point_value=point_values[pos.symbol],
            slippage_ticks_per_side=slip, commission_usd=comm,
            stop_loss_usd_per_contract=stop_usd,
            window_max_high=wmax, window_min_low=wmin,
        )
        trade = Trade(
            trade_id=pos.trade_id,
            entry_ts=pos.entry_ts,
            exit_ts=pos.exit_ts,
            symbol=pos.symbol,
            direction=pos.direction,
            contracts=pos.contracts,
            entry_price=pos.entry_price,
            exit_price=pos.entry_price * float(np.exp(pos.realized_logret)),
            pnl_usd=pnl,
            pnl_reason=reason,
        )
        if account.status == "active":
            account.on_trade_close(trade)

    for sig in signals:
        if account.status != "active":
            break
        last_date = max(last_date, sig.ts_decision.date())

        # Close any positions due before this signal's decision time
        while pending_exits and pending_exits[0][0] <= sig.ts_decision:
            _, _, pos = heapq.heappop(pending_exits)
            close_position(pos)
            open_symbols.discard(pos.symbol)
            if account.status != "active":
                break
        if account.status != "active":
            break

        # One position per symbol
        if sig.symbol in open_symbols:
            continue

        decision = risk_manager.decide(
            account=account, firm=firm, symbol=sig.symbol, horizon_key=sig.horizon_key,
            ts_decision=sig.ts_decision, p_proba=sig.p_proba, threshold=sig.threshold,
            sizing_method=sizing_method, sizing_params=sizing_params, direction_min_gap=dir_gap,
            max_contracts=effective_max,
        )
        if not decision.take:
            continue

        # Entry with jitter (anti-bot): shift entry timestamp 0-59s
        jitter = int(rng.integers(0, 60))
        entry_ts = sig.ts_decision + dt.timedelta(seconds=jitter)
        exit_ts = sig.ts_decision + dt.timedelta(minutes=sig.horizon_minutes)
        trade_counter += 1
        pos = OpenPosition(
            symbol=sig.symbol, horizon_key=sig.horizon_key,
            signal_ts=pd.Timestamp(sig.ts_decision),
            entry_ts=entry_ts, exit_ts=exit_ts,
            direction=decision.direction, contracts=decision.contracts,
            entry_price=sig.entry_price, realized_logret=sig.realized_logret,
            trade_id=f"{account.account_id}_T{trade_counter:05d}",
        )
        heapq.heappush(pending_exits, (exit_ts, seq, pos))
        seq += 1
        open_symbols.add(sig.symbol)

    # Drain remaining positions
    while pending_exits and account.status == "active":
        _, _, pos = heapq.heappop(pending_exits)
        close_position(pos)
        last_date = max(last_date, pos.exit_ts.date())

    account.finalize(last_date)
    return account


# ---------------------------------------------------------------------------
# CLI: run ONE account and print a summary
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--firm", default="topstep")
    p.add_argument("--firm-config", default=None, help="path to firm yaml; default config/firms/{firm}_50k.yaml")
    p.add_argument("--strategy", default=str(EXPERIMENT_DIR / "config" / "strategy_v0.yaml"))
    p.add_argument("--seed", type=int, default=42)
    args = p.parse_args(argv)

    strategy_cfg = yaml.safe_load(Path(args.strategy).read_text(encoding="utf-8"))
    firm_path = Path(args.firm_config) if args.firm_config else (EXPERIMENT_DIR / "config" / "firms" / f"{args.firm}_50k.yaml")
    firm = load_firm_config(firm_path)

    preds_dir = (EXPERIMENT_DIR / strategy_cfg["model_predictions_dir"]).resolve()
    print(f"Loading signals from {preds_dir} ...")
    signals = load_signals(strategy_cfg, preds_dir)
    print(f"  {len(signals):,} signals across {len(strategy_cfg['active_cells'])} active cells")
    if signals:
        print(f"  date range: {signals[0].ts_decision.date()} - {signals[-1].ts_decision.date()}")

    excursions = load_excursions(EXPERIMENT_DIR / "out" / "excursions.parquet")
    print(f"  loaded {len(excursions):,} precomputed excursions"
          + ("" if excursions else "  (none — stops disabled)"))

    sim_start = signals[0].ts_decision.date() if signals else dt.date(2021, 1, 1)
    account = Account(account_id=f"{args.firm}_50k_{args.seed:03d}", firm=firm, sim_start_date=sim_start)
    simulate_account(account=account, signals=signals, firm=firm, strategy_cfg=strategy_cfg,
                     jitter_seed=args.seed, excursions=excursions)

    print(f"\n=== {account.account_id} result ===")
    print(f"  status:                 {account.status}")
    if account.blown_reason:
        print(f"  blown_reason:           {account.blown_reason}")
    print(f"  final balance:          ${account.balance:,.0f}")
    print(f"  profit above starting:  ${account.profit_above_starting:,.0f}")
    print(f"  total payouts:          ${account.total_payouts_received:,.0f}  ({len(account.payouts)} payouts)")
    print(f"  total $ collected:      ${account.total_pnl_collected:,.0f}")
    print(f"  trades:                 {len(account.trades):,}")
    print(f"  trade days:             {len(account.trade_days)}")
    print(f"  EOD high water:         ${account.eod_balance_high_water:,.0f}")
    if account.payouts:
        print(f"  payout log:")
        for po in account.payouts[:10]:
            print(f"    {po.ts.date()}  ${po.amount:,.0f}  (bal ${po.balance_before:,.0f} -> ${po.balance_after:,.0f})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
