"""Pull ETHUSDT funding + spot/perp klines (free Binance archive) for the
cross-crypto feature block — the "newer/less-arbed" hypothesis in feature form.

Run: backend/.venv/Scripts/python.exe experiments/btc_model_v0/pull_eth.py
Artifacts: data/eth_funding.parquet, data/eth_spot_1d.parquet, data/eth_perp_1d.parquet
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

MODULE = Path(__file__).resolve().parent
sys.path.insert(0, str(MODULE))
from pull_crypto_aux import BASE, OUT, fetch_zip_csv, months  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")

KCOLS = ["open_time", "open", "high", "low", "close", "volume", "close_time",
         "qvol", "n", "tbv", "tqv", "ig"]


def pull_klines_sym(symbol: str, market: str, interval: str, start: str, name: str) -> None:
    frames = []
    base = f"{BASE}/{market}/monthly/klines/{symbol}/{interval}"
    for m in months(start, "2026-06"):
        df = fetch_zip_csv(f"{base}/{symbol}-{interval}-{m}.zip")
        if df is None:
            continue
        df = df.iloc[:, :12]
        df.columns = KCOLS
        ot = pd.to_numeric(df["open_time"], errors="coerce")
        unit = "us" if ot.iloc[0] > 1e14 else "ms"
        frames.append(pd.DataFrame({"ts": pd.to_datetime(ot, unit=unit, utc=True),
                                    "close": pd.to_numeric(df["close"], errors="coerce")}))
    s = pd.concat(frames).dropna().sort_values("ts").reset_index(drop=True)
    s.to_parquet(OUT / f"{name}.parquet")
    print(f"{name}: {len(s)} rows {s['ts'].min()} -> {s['ts'].max()}")


def pull_eth_funding() -> None:
    frames = []
    for m in months("2019-11", "2026-06"):
        df = fetch_zip_csv(f"{BASE}/futures/um/monthly/fundingRate/ETHUSDT/ETHUSDT-fundingRate-{m}.zip")
        if df is None:
            continue
        cols = {str(c).lower(): c for c in df.columns}
        tcol = next((cols[c] for c in cols if "time" in c), df.columns[0])
        rcol = next((cols[c] for c in cols if "rate" in c and "interval" not in c), df.columns[-1])
        frames.append(pd.DataFrame({"ts": pd.to_datetime(df[tcol], unit="ms", utc=True),
                                    "rate": pd.to_numeric(df[rcol], errors="coerce")}))
    f = pd.concat(frames).dropna().sort_values("ts").reset_index(drop=True)
    f.to_parquet(OUT / "eth_funding.parquet")
    print(f"eth_funding: {len(f)} rows {f['ts'].min()} -> {f['ts'].max()}")


if __name__ == "__main__":
    pull_eth_funding()
    pull_klines_sym("ETHUSDT", "spot", "1d", "2017-08", "eth_spot_1d")
    pull_klines_sym("ETHUSDT", "futures/um", "1d", "2019-11", "eth_perp_1d")
    print("done")
