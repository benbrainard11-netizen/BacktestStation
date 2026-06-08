"""BacktestStation backend -- status page only.

The research lab is backend + tools, run via CLI / Python (the engine, sims,
ingest, and research modules are imported or invoked from the command line).
This FastAPI app exists only to serve a small read-only status dashboard at `/`
plus a JSON summary at `/api/status`. No CRUD API, no strategy/backtest HTTP
endpoints -- run those as tools.
"""

from __future__ import annotations

import datetime as _dt
import json

from fastapi import FastAPI
from fastapi.responses import HTMLResponse

from app import __version__

app = FastAPI(
    title="BacktestStation",
    version=__version__,
    description="Research lab -- backend + tools (read-only status page)",
)


def _recent_runs(limit: int = 10) -> list[dict]:
    """Last N backtest runs from meta.sqlite. Best-effort."""
    try:
        from sqlalchemy import select

        from app.db.models import BacktestRun
        from app.db.session import make_engine, make_session_factory

        factory = make_session_factory(make_engine())
        with factory() as session:
            rows = (
                session.execute(
                    select(BacktestRun)
                    .order_by(BacktestRun.created_at.desc())
                    .limit(limit)
                )
                .scalars()
                .all()
            )
            return [
                {
                    "id": r.id,
                    "symbol": r.symbol,
                    "source": r.source,
                    "status": r.status,
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                }
                for r in rows
            ]
    except Exception as exc:  # noqa: BLE001 -- status page is best-effort
        return [{"error": f"{type(exc).__name__}: {exc}"}]


def _r2_status() -> dict:
    """R2 raw-warehouse mirror freshness. Best-effort (needs BS_R2_* env)."""
    try:
        from app.ingest.r2_client import make_s3_client

        client, bucket = make_s3_client()
        obj = client.get_object(Bucket=bucket, Key="_inventory.json")
        inv = json.loads(obj["Body"].read())
        parts = inv.get("partitions")
        n_parts = (
            len(parts)
            if isinstance(parts, list)
            else parts
            if isinstance(parts, int)
            else len(inv.get("files") or [])
        )
        return {
            "bucket": bucket,
            "generated_at": inv.get("generated_at"),
            "partitions": n_parts,
        }
    except Exception as exc:  # noqa: BLE001
        return {"error": f"{type(exc).__name__}: {exc}"}


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "version": __version__}


@app.get("/api/status")
def status() -> dict:
    return {
        "ok": True,
        "version": __version__,
        "checked_at": _dt.datetime.now(_dt.timezone.utc).isoformat(),
        "recent_runs": _recent_runs(),
        "r2": _r2_status(),
    }


_PAGE = """<!doctype html><html><head><meta charset="utf-8">
<title>BacktestStation status</title>
<style>
body{background:#09090b;color:#e4e4e7;font:14px/1.5 system-ui,sans-serif;margin:0;padding:24px}
h1{font-size:18px;margin:0 0 2px}.muted{color:#a1a1aa;font-size:12px}
.card{background:#18181b;border:1px solid #27272a;border-radius:8px;padding:16px;margin:16px 0;max-width:780px}
table{width:100%;border-collapse:collapse;font-size:13px}td,th{text-align:left;padding:4px 8px;border-bottom:1px solid #27272a}
.k{color:#a1a1aa}.err{color:#fb7185}b{color:#fafafa}
</style></head><body>
<h1>BacktestStation <span class="muted">research lab - backend + tools</span></h1>
<div class="muted">read-only status. tools (engine, sims, ingest, research) run via CLI / Python, not here.</div>
<div id="root"><div class="card">loading...</div></div>
<script>
async function load(){
  try{
    const d = await (await fetch('/api/status')).json();
    const r2 = d.r2.error ? `<span class="err">${d.r2.error}</span>`
      : `bucket <b>${d.r2.bucket}</b> &middot; ${d.r2.partitions} partitions &middot; updated ${d.r2.generated_at||'?'}`;
    let runs;
    if (d.recent_runs.length && d.recent_runs[0].error) runs = `<span class="err">${d.recent_runs[0].error}</span>`;
    else if (!d.recent_runs.length) runs = '<span class="muted">no runs</span>';
    else runs = '<table><tr><th>id</th><th>symbol</th><th>source</th><th>status</th><th>created</th></tr>'+
      d.recent_runs.map(x=>`<tr><td>${x.id}</td><td>${x.symbol||''}</td><td>${x.source||''}</td><td>${x.status||''}</td><td class="k">${x.created_at||''}</td></tr>`).join('')+'</table>';
    document.getElementById('root').innerHTML =
      `<div class="card"><b>backend</b> &#10003; running &middot; v${d.version} <span class="muted">&middot; checked ${d.checked_at}</span></div>`+
      `<div class="card"><b>R2 warehouse mirror</b><div style="margin-top:6px">${r2}</div></div>`+
      `<div class="card"><b>recent backtest runs</b><div style="margin-top:8px">${runs}</div></div>`;
  }catch(e){ document.getElementById('root').innerHTML = `<div class="card err">status fetch failed: ${e}</div>`; }
}
load(); setInterval(load, 30000);
</script></body></html>"""


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return _PAGE
