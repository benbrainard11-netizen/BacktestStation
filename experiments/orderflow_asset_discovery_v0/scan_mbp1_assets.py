"""Scout full-universe MBP-1 orderflow by symbol.

Reads mirrored MBP-1 parquet, emits 15-minute orderflow buckets, then builds a
symbol scoreboard from liquidity, spread cost, coverage, and simple next-bucket
orderflow correlations. This is a pre-model triage pass, not a trading result.
"""

from __future__ import annotations

import argparse
import datetime as dt
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

THIS_FILE = Path(__file__).resolve()
EXPERIMENT_DIR = THIS_FILE.parent
REPO_ROOT = EXPERIMENT_DIR.parents[1]
sys.path.insert(0, str(REPO_ROOT / "backend"))

from app.ingest.cost_estimator import UNIVERSE  # noqa: E402

MBP1_ROOT = Path("D:/data/raw/databento/mbp-1")
OUT_ROOT = EXPERIMENT_DIR / "out"
BUCKET_ROOT = OUT_ROOT / "buckets_15m"
REPORT_DIR = EXPERIMENT_DIR / "report"
BUCKET = "15min"
EPS = 1e-12

READ_COLS = [
    "ts_event",
    "action",
    "side",
    "size",
    "bid_px",
    "ask_px",
    "bid_sz",
    "ask_sz",
    "bid_ct",
    "ask_ct",
]

BUCKET_COLS = [
    "ts_event",
    "symbol",
    "date",
    "event_count",
    "trade_count",
    "volume",
    "net_signed",
    "signed_ratio",
    "imb_mean",
    "imb_last",
    "micro_drift",
    "spread_mean",
    "spread_bps_mean",
    "depth_mean",
    "order_count_mean",
    "cancel_add",
    "ret_pts",
    "ret_log",
    "absorption",
]


def default_symbols() -> list[str]:
    symbols: list[str] = []
    for group in UNIVERSE.values():
        for symbol in group:
            if symbol not in symbols:
                symbols.append(symbol)
    return symbols


def parse_date(value: str | None) -> dt.date | None:
    return dt.date.fromisoformat(value) if value else None


def partition_dates(symbol: str, start: dt.date | None, end: dt.date | None) -> list[tuple[dt.date, Path]]:
    sym_dir = MBP1_ROOT / f"symbol={symbol}"
    if not sym_dir.exists():
        return []

    out: list[tuple[dt.date, Path]] = []
    for part in sorted(sym_dir.glob("date=*")):
        try:
            day = dt.date.fromisoformat(part.name.removeprefix("date="))
        except ValueError:
            continue
        if start and day < start:
            continue
        if end and day > end:
            continue
        path = part / "part-000.parquet"
        if path.exists() and path.stat().st_size > 0:
            out.append((day, path))
    return out


def compute_buckets(path: Path, symbol: str, day: dt.date) -> pd.DataFrame:
    df = pd.read_parquet(path, columns=READ_COLS)
    if df.empty:
        return pd.DataFrame(columns=BUCKET_COLS)

    bid = df["bid_px"].astype("f8")
    ask = df["ask_px"].astype("f8")
    bid_sz = df["bid_sz"].astype("f8")
    ask_sz = df["ask_sz"].astype("f8")
    total_sz = (bid_sz + ask_sz).replace(0, np.nan)
    mid = (bid + ask) / 2.0
    micro = (bid * ask_sz + ask * bid_sz) / total_sz
    spread = ask - bid

    is_trade = (df["action"] == "T").to_numpy()
    side = df["side"].to_numpy()
    sign = np.where(side == "B", 1.0, np.where(side == "A", -1.0, 0.0))
    size = df["size"].astype("f8").to_numpy()
    signed = np.where(is_trade, sign * size, 0.0)
    traded_size = np.where(is_trade, size, 0.0)

    work = pd.DataFrame(
        {
            "mid": mid.to_numpy(),
            "spread": spread.to_numpy(),
            "spread_bps": (spread / mid * 10_000.0).to_numpy(),
            "imb": ((bid_sz - ask_sz) / total_sz).to_numpy(),
            "micro_drift": (micro - mid).to_numpy(),
            "depth": (bid_sz + ask_sz).to_numpy(),
            "order_count": (df["bid_ct"].astype("f8") + df["ask_ct"].astype("f8")).to_numpy(),
            "signed": signed,
            "traded_size": traded_size,
            "is_trade": is_trade.astype("f8"),
            "is_add": (df["action"] == "A").to_numpy().astype("f8"),
            "is_cancel": (df["action"] == "C").to_numpy().astype("f8"),
        },
        index=pd.DatetimeIndex(pd.to_datetime(df["ts_event"], utc=True)),
    )

    grouped = work.resample(BUCKET, label="left", closed="left")
    out = pd.DataFrame(
        {
            "event_count": grouped["mid"].size(),
            "trade_count": grouped["is_trade"].sum(),
            "volume": grouped["traded_size"].sum(),
            "net_signed": grouped["signed"].sum(),
            "imb_mean": grouped["imb"].mean(),
            "imb_last": grouped["imb"].last(),
            "micro_drift": grouped["micro_drift"].mean(),
            "spread_mean": grouped["spread"].mean(),
            "spread_bps_mean": grouped["spread_bps"].mean(),
            "depth_mean": grouped["depth"].mean(),
            "order_count_mean": grouped["order_count"].mean(),
            "ret_pts": grouped["mid"].last() - grouped["mid"].first(),
            "ret_log": np.log(grouped["mid"].last() / grouped["mid"].first()),
        }
    )
    add_count = grouped["is_add"].sum()
    out["cancel_add"] = grouped["is_cancel"].sum() / add_count.where(add_count > 0, np.nan)
    out["signed_ratio"] = out["net_signed"] / out["volume"].where(out["volume"] > 0, np.nan)
    out["absorption"] = out["net_signed"].abs() / (out["ret_pts"].abs() + EPS)

    out = out.reset_index().rename(columns={"index": "ts_event"})
    out["symbol"] = symbol
    out["date"] = day.isoformat()
    return out[BUCKET_COLS]


def write_symbol_buckets(
    symbol: str,
    parts: list[tuple[dt.date, Path]],
    *,
    rebuild: bool,
) -> tuple[int, int]:
    sym_out = BUCKET_ROOT / f"symbol={symbol}"
    sym_out.mkdir(parents=True, exist_ok=True)
    written = skipped = 0
    for day, src in parts:
        dst = sym_out / f"date={day.isoformat()}.parquet"
        if dst.exists() and not rebuild:
            skipped += 1
            continue
        buckets = compute_buckets(src, symbol, day)
        buckets.to_parquet(dst, index=False)
        written += 1
    return written, skipped


def load_bucket_outputs(symbols: list[str], start: dt.date | None, end: dt.date | None) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    for symbol in symbols:
        sym_dir = BUCKET_ROOT / f"symbol={symbol}"
        if not sym_dir.exists():
            continue
        for path in sorted(sym_dir.glob("date=*.parquet")):
            try:
                day = dt.date.fromisoformat(path.stem.removeprefix("date="))
            except ValueError:
                continue
            if start and day < start:
                continue
            if end and day > end:
                continue
            frames.append(pd.read_parquet(path))
    if not frames:
        return pd.DataFrame(columns=BUCKET_COLS)
    out = pd.concat(frames, ignore_index=True)
    out["ts_event"] = pd.to_datetime(out["ts_event"], utc=True)
    return out.sort_values(["symbol", "ts_event"]).reset_index(drop=True)


def _corr(a: pd.Series, b: pd.Series, method: str = "spearman") -> float:
    valid = ~(a.isna() | b.isna())
    if int(valid.sum()) < 30:
        return float("nan")
    return float(a[valid].corr(b[valid], method=method))


def build_scoreboard(buckets: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    if buckets.empty:
        return pd.DataFrame(), pd.DataFrame()

    buckets = buckets.copy()
    buckets["next_ret_log"] = buckets.groupby("symbol")["ret_log"].shift(-1)
    buckets["next_abs_ret_log"] = buckets["next_ret_log"].abs()
    buckets["date"] = buckets["date"].astype(str)

    daily = buckets.groupby(["symbol", "date"]).agg(
        buckets=("ts_event", "count"),
        event_count=("event_count", "sum"),
        trade_count=("trade_count", "sum"),
        volume=("volume", "sum"),
        spread_bps_mean=("spread_bps_mean", "mean"),
        spread_bps_p95=("spread_bps_mean", lambda s: float(s.quantile(0.95))),
        depth_mean=("depth_mean", "mean"),
        cancel_add=("cancel_add", "mean"),
    ).reset_index()

    rows: list[dict] = []
    for symbol, group in buckets.groupby("symbol"):
        active = group[group["event_count"] > 0]
        trade_active = group[group["trade_count"] > 0]
        rows.append(
            {
                "symbol": symbol,
                "coverage_days": int(group["date"].nunique()),
                "bucket_count": int(len(group)),
                "active_bucket_pct": float((group["event_count"] > 0).mean()),
                "trade_bucket_pct": float((group["trade_count"] > 0).mean()),
                "mean_events_per_bucket": float(active["event_count"].mean()),
                "mean_trades_per_bucket": float(trade_active["trade_count"].mean()),
                "mean_volume_per_bucket": float(trade_active["volume"].mean()),
                "median_spread_bps": float(active["spread_bps_mean"].median()),
                "p95_spread_bps": float(active["spread_bps_mean"].quantile(0.95)),
                "mean_depth": float(active["depth_mean"].mean()),
                "mean_cancel_add": float(active["cancel_add"].mean()),
                "signed_next_ic": _corr(group["signed_ratio"], group["next_ret_log"]),
                "imb_next_ic": _corr(group["imb_mean"], group["next_ret_log"]),
                "micro_next_ic": _corr(group["micro_drift"], group["next_ret_log"]),
                "absorption_next_abs_ret_ic": _corr(group["absorption"], group["next_abs_ret_log"]),
            }
        )
    scoreboard = pd.DataFrame(rows)
    return daily, score_symbols(scoreboard)


def score_symbols(scoreboard: pd.DataFrame) -> pd.DataFrame:
    out = scoreboard.copy()
    if out.empty:
        return out

    liquidity = np.log1p(out["mean_trades_per_bucket"].fillna(0)).rank(pct=True)
    depth = np.log1p(out["mean_depth"].fillna(0)).rank(pct=True)
    coverage = out["coverage_days"].fillna(0).rank(pct=True)
    cost = 1.0 - out["median_spread_bps"].replace([np.inf, -np.inf], np.nan).fillna(1e9).rank(pct=True)
    signal = out[["signed_next_ic", "imb_next_ic", "micro_next_ic"]].abs().max(axis=1).fillna(0).rank(pct=True)
    out["liquidity_score"] = liquidity
    out["cost_score"] = cost
    out["coverage_score"] = coverage
    out["signal_probe_score"] = signal
    out["discovery_score"] = (
        0.35 * liquidity
        + 0.25 * cost
        + 0.20 * coverage
        + 0.10 * depth
        + 0.10 * signal
    )
    return out.sort_values("discovery_score", ascending=False).reset_index(drop=True)


def write_report(scoreboard: pd.DataFrame, daily: pd.DataFrame, args: argparse.Namespace) -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    path = REPORT_DIR / "asset_discovery_summary.md"
    lines = [
        "# Orderflow Asset Discovery",
        "",
        f"Generated: {dt.datetime.now(dt.timezone.utc).isoformat()}",
        f"Window: {args.start or 'first'} -> {args.end or 'last'}",
        f"Symbols scanned: {scoreboard['symbol'].nunique() if not scoreboard.empty else 0}",
        f"Symbol-days summarized: {len(daily):,}",
        "",
        "## Top Symbols",
        "",
        "| rank | symbol | score | days | med spread bps | trades/bucket | signed IC | imb IC | micro IC |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for i, row in scoreboard.head(15).iterrows():
        lines.append(
            f"| {i + 1} | {row['symbol']} | {row['discovery_score']:.3f} | "
            f"{int(row['coverage_days'])} | {row['median_spread_bps']:.4f} | "
            f"{row['mean_trades_per_bucket']:.1f} | {row['signed_next_ic']:.4f} | "
            f"{row['imb_next_ic']:.4f} | {row['micro_next_ic']:.4f} |"
        )
    lines.extend(
        [
            "",
            "## Notes",
            "",
            "- `discovery_score` is a triage score, not a P&L result.",
            "- Correlations are next-15-minute probes and can be contrarian.",
            "- Good candidates still need explicit spread/slippage and walk-forward tests.",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def run(args: argparse.Namespace) -> int:
    start = parse_date(args.start)
    end = parse_date(args.end)
    symbols = args.symbols or default_symbols()

    BUCKET_ROOT.mkdir(parents=True, exist_ok=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"symbols={len(symbols)} start={start} end={end}")

    for symbol in symbols:
        t0 = time.time()
        parts = partition_dates(symbol, start, end)
        if args.limit_days:
            parts = parts[: args.limit_days]
        written, skipped = write_symbol_buckets(symbol, parts, rebuild=args.rebuild)
        print(
            f"{symbol:7s} parts={len(parts):4d} wrote={written:4d} "
            f"skipped={skipped:4d} sec={time.time() - t0:.1f}",
            flush=True,
        )

    buckets = load_bucket_outputs(symbols, start, end)
    daily, scoreboard = build_scoreboard(buckets)
    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    daily.to_csv(OUT_ROOT / "daily_summary.csv", index=False)
    scoreboard.to_csv(OUT_ROOT / "symbol_scoreboard.csv", index=False)
    write_report(scoreboard, daily, args)
    print(f"wrote {OUT_ROOT / 'symbol_scoreboard.csv'}")
    print(f"wrote {REPORT_DIR / 'asset_discovery_summary.md'}")
    return 0


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Scan all MBP-1 assets for orderflow candidates.")
    parser.add_argument("--symbols", nargs="+", default=None)
    parser.add_argument("--start", default=None, help="YYYY-MM-DD inclusive")
    parser.add_argument("--end", default=None, help="YYYY-MM-DD inclusive")
    parser.add_argument("--limit-days", type=int, default=None)
    parser.add_argument("--rebuild", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    return run(parse_args(argv))


if __name__ == "__main__":
    raise SystemExit(main())
