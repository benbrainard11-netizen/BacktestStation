"""Pull BTC perp funding-rate history + spot daily klines from Binance public archive.

Free, keyless, monthly zip files from data.binance.vision. Funding (BTCUSDT-PERP)
exists from 2019-09; spot 1d klines from 2017-08. Saved to data/funding.parquet and
data/spot_1d.parquet. These feed the documented feature blocks: funding level/extremes
and CME-futures-vs-spot basis.

Run: backend/.venv/Scripts/python.exe experiments/btc_model_v0/pull_crypto_aux.py
"""

from __future__ import annotations

import io
import sys
import urllib.request
import zipfile
from pathlib import Path

import pandas as pd

MODULE = Path(__file__).resolve().parent
OUT = MODULE / "data"
BASE = "https://data.binance.vision/data"

sys.stdout.reconfigure(encoding="utf-8")


def months(start: str, end: str):
    return [p.strftime("%Y-%m") for p in pd.period_range(start, end, freq="M")]


def fetch_zip_csv(url: str) -> pd.DataFrame | None:
    try:
        with urllib.request.urlopen(url, timeout=30) as r:
            buf = io.BytesIO(r.read())
    except Exception as e:  # noqa: BLE001
        print(f"  miss {url.rsplit('/', 1)[-1]}: {type(e).__name__}")
        return None
    with zipfile.ZipFile(buf) as z:
        name = z.namelist()[0]
        raw = z.read(name)
    first = raw.split(b"\n", 1)[0]
    has_header = any(c.isalpha() for c in first.decode(errors="ignore"))
    return pd.read_csv(io.BytesIO(raw), header=0 if has_header else None)


def pull_funding() -> None:
    frames = []
    for m in months("2019-09", "2026-06"):
        df = fetch_zip_csv(f"{BASE}/futures/um/monthly/fundingRate/BTCUSDT/BTCUSDT-fundingRate-{m}.zip")
        if df is None:
            continue
        cols = {str(c).lower(): c for c in df.columns}
        tcol = next((cols[c] for c in cols if "time" in c), df.columns[0])
        rcol = next((cols[c] for c in cols if "rate" in c and "interval" not in c), df.columns[-1])
        frames.append(pd.DataFrame({"ts": pd.to_datetime(df[tcol], unit="ms", utc=True),
                                    "rate": pd.to_numeric(df[rcol], errors="coerce")}))
    f = pd.concat(frames).dropna().sort_values("ts").reset_index(drop=True)
    f.to_parquet(OUT / "funding.parquet")
    print(f"funding: {len(f)} rows {f['ts'].min()} -> {f['ts'].max()}")


def pull_spot() -> None:
    frames = []
    kcols = ["open_time", "open", "high", "low", "close", "volume", "close_time",
             "qvol", "n", "tbv", "tqv", "ig"]
    for m in months("2017-08", "2026-06"):
        df = fetch_zip_csv(f"{BASE}/spot/monthly/klines/BTCUSDT/1d/BTCUSDT-1d-{m}.zip")
        if df is None:
            continue
        df = df.iloc[:, :12]
        df.columns = kcols
        ot = pd.to_numeric(df["open_time"], errors="coerce")
        unit = "us" if ot.iloc[0] > 1e14 else "ms"
        frames.append(pd.DataFrame({"ts": pd.to_datetime(ot, unit=unit, utc=True),
                                    "close": pd.to_numeric(df["close"], errors="coerce")}))
    s = pd.concat(frames).dropna().sort_values("ts").reset_index(drop=True)
    s.to_parquet(OUT / "spot_1d.parquet")
    print(f"spot: {len(s)} rows {s['ts'].min()} -> {s['ts'].max()}")


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    pull_funding()
    pull_spot()
    print("done")
