"""GO/NO-GO for NDX self-compute: the greeks endpoint is NO_DATA for NDX, but do the RAW
inputs (option prices + open interest + index spot) exist? If yes, we can compute IV->BS
gamma->walls ourselves. Tests one NDX expiration per year across the raw endpoints.
Run with a Terminal serving on 25510.
"""
import datetime as dt
import sys
import requests

B = "http://127.0.0.1:25510/v2"
ROOT = sys.argv[1] if len(sys.argv) > 1 else "NDXP"


def J(path, **p):
    try:
        r = requests.get(f"{B}/{path}", params=p, timeout=60)
        body = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
        resp = body.get("response")
        n = len(resp) if isinstance(resp, list) else 0
        # peek at what fields a row carries (for the price/IV we'd need)
        fmt = body.get("header", {}).get("format", [])
        return f"http={r.status_code} rows={n}" + (f" fmt={fmt}" if n and fmt else "")
    except Exception as ex:
        return f"ERR {str(ex)[:40]}"


try:
    exps = [int(e) for e in requests.get(f"{B}/list/expirations", params={"root": ROOT}, timeout=30).json()["response"]]
except Exception as e:
    print(f"terminal not serving / root bad: {e}")
    raise SystemExit(1)
print(f"{ROOT}: {len(exps)} expirations listed ({min(exps)}..{max(exps)})\n")

# EOD endpoints only (no ivl needed): eod = the raw price report (OHLC + bid/ask at close,
# enough for mid -> IV), open_interest = OI, eod_greeks = control (expect NO_DATA for NDX).
endpoints = ["bulk_hist/option/eod", "bulk_hist/option/open_interest", "bulk_hist/option/eod_greeks"]
for yr in (2020, 2022, 2024, 2026):
    cand = [e for e in exps if str(e).startswith(str(yr))]
    if not cand:
        print(f"{yr}: (no expirations listed)")
        continue
    e = cand[len(cand) // 2]
    ed = dt.datetime.strptime(str(e), "%Y%m%d")
    sd = (ed - dt.timedelta(days=7)).strftime("%Y%m%d")
    print(f"{yr}  exp={e}:")
    for ep in endpoints:
        print(f"   {ep:34s} {J(ep, root=ROOT, exp=e, start_date=sd, end_date=str(e))}")
    print()

print("NDX index spot (hist/index/eod):", J("hist/index/eod", root="NDX", start_date="20220103", end_date="20220110"))
