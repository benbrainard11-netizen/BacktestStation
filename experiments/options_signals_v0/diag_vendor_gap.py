"""Settle it: does the vendor actually HAVE SPX eod_greeks per year, or is the
2021-2022 'gap' a hard vendor cap (NO_DATA)? Direct terminal requests, one sample
expiration per year. Run only with the Terminal serving.
"""
import datetime as dt
import sys
import requests

B = "http://127.0.0.1:25510/v2"
ROOT = sys.argv[1] if len(sys.argv) > 1 else "SPXW"


def J(path, **p):
    return requests.get(f"{B}/{path}", params=p, timeout=90)


try:
    exps = J("list/expirations", root=ROOT).json().get("response", [])
except Exception as e:
    print(f"could not list expirations (terminal not serving?): {e}")
    raise SystemExit(1)
exps = [int(e) for e in exps]
print(f"{ROOT}: {len(exps)} expirations listed  ({min(exps)}..{max(exps)})\n")
print(f"{'year':>5} {'sample_exp':>10} {'http':>5} {'contracts':>10}  note")
for yr in (2019, 2020, 2021, 2022, 2023, 2024, 2025, 2026):
    cand = [e for e in exps if str(e).startswith(str(yr))]
    if not cand:
        print(f"{yr:>5} {'-':>10} {'-':>5} {'-':>10}  no expirations listed for year")
        continue
    e = cand[len(cand) // 2]
    ed = dt.datetime.strptime(str(e), "%Y%m%d")
    sd = (ed - dt.timedelta(days=7)).strftime("%Y%m%d")
    try:
        r = J("bulk_hist/option/eod_greeks", root=ROOT, exp=e, start_date=sd, end_date=str(e))
        body = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
        resp = body.get("response")
        n = len(resp) if isinstance(resp, list) else 0
        err = body.get("header", {}).get("error_type") or body.get("header", {}).get("error_msg") or ""
        note = "DATA OK" if n else f"NO DATA (http {r.status_code}) {err}".strip()
        print(f"{yr:>5} {e:>10} {r.status_code:>5} {n:>10}  {note}")
    except Exception as ex:
        print(f"{yr:>5} {e:>10} {'ERR':>5} {'-':>10}  {ex}")
