"""Pull the SPX+NDX EOD option-chain bundle from Databento OPRA for the GEX backtest.

~$75, 1 year (2025), the bundle priced + verified 2026-06-02:
  definition (strikes/expiries/type/multiplier) + statistics (open interest) + ohlcv-1d (EOD prices -> IV).
SPX.OPT + NDX.OPT via parent symbology. Chunked MONTHLY (a full-year request 504-times-out server-side)
with retry on transient gateway errors. Streams straight to DBN.zst (memory-safe via path=). Idempotent:
skips months already present. Raw + append-only (D:/data/raw/opra/). A failed/timed-out request does NOT
bill -- billing is on successful delivery, so retrying is safe and only the data that lands is charged.

Run: backend/.venv/Scripts/python.exe experiments/options_signals_v0/pull_opra.py
"""
from __future__ import annotations

import os
import time
from pathlib import Path

for envf in [".env", "backend/.env"]:
    p = Path(envf)
    if p.exists():
        for ln in p.read_text(errors="replace").splitlines():
            if ln.strip().startswith("DATABENTO_API_KEY"):
                os.environ["DATABENTO_API_KEY"] = ln.split("=", 1)[1].strip().strip('"').strip("'")

import databento as db  # noqa: E402

RAW = Path("D:/data/raw/opra")
DATASET = "OPRA.PILLAR"
ROOTS = ["SPX.OPT", "NDX.OPT"]
SCHEMAS = ["definition", "statistics", "ohlcv-1d"]


def months(y0: int, m0: int, y1: int, m1: int) -> list[tuple[str, str]]:
    out, y, m = [], y0, m0
    while (y, m) < (y1, m1):
        ny, nm = (y + 1, 1) if m == 12 else (y, m + 1)
        out.append((f"{y:04d}-{m:02d}-01", f"{ny:04d}-{nm:02d}-01"))
        y, m = ny, nm
    return out


def pull_one(client, root, sch, s, e, out: Path) -> float:
    for attempt in range(5):
        try:
            client.timeseries.get_range(
                dataset=DATASET, schema=sch, symbols=[root], stype_in="parent",
                start=s, end=e, path=str(out),
            )
            return out.stat().st_size / 1e6
        except Exception as ex:  # noqa: BLE001
            msg = str(ex)
            transient = any(k in msg for k in ("504", "502", "timed out", "timeout", "Connection"))
            if transient and attempt < 4:
                if out.exists():
                    out.unlink()  # drop any partial
                time.sleep(5 * (attempt + 1))
                continue
            raise


def main() -> int:
    client = db.Historical(key=os.environ["DATABENTO_API_KEY"])
    total = 0.0
    for root in ROOTS:
        for sch in SCHEMAS:
            outdir = RAW / sch
            outdir.mkdir(parents=True, exist_ok=True)
            for s, e in months(2025, 1, 2026, 1):
                out = outdir / f"{root.replace('.', '_')}_{s[:7]}.dbn.zst"
                if out.exists() and out.stat().st_size > 0:
                    print(f"skip {out.name}", flush=True)
                    continue
                print(f"pulling {root} {sch} {s[:7]} ...", flush=True)
                mb = pull_one(client, root, sch, s, e, out)
                total += mb
                print(f"  wrote {out.name} ({mb:,.0f} MB)  [running total {total:,.0f} MB]", flush=True)
    print(f"DONE — {total:,.0f} MB across {RAW}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
