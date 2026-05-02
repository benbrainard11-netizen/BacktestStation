"""BacktestStation cloud warehouse client.

Reads parquet partitions from a Cloudflare R2 mirror with a local
on-disk cache, so collaborators can run BacktestStation backtests
against Ben's curated warehouse without needing direct disk access.

Public API mirrors `app.data.reader` from the BacktestStation backend:

    from bsdata import load_bars, load_tbbo, load_mbp1, get_inventory

    df = load_bars(symbol="NQ.c.0", start="2026-04-01", end="2026-04-25", timeframe="1m")

Required env vars:
    BS_R2_BUCKET     (default: bsdata-prod)
    BS_R2_ENDPOINT   (https://<account>.r2.cloudflarestorage.com)
    BS_R2_ACCESS_KEY (read-scope token)
    BS_R2_SECRET     (read-scope token)

Optional:
    BS_R2_CACHE_ROOT (default: ~/.bsdata/cache)

See README.md for one-time setup.
"""

from bsdata.inventory import get_inventory
from bsdata.loader import load_bars, load_mbp1, load_tbbo

__all__ = ["get_inventory", "load_bars", "load_mbp1", "load_tbbo"]
__version__ = "0.1.0"
