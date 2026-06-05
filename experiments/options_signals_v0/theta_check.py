"""Probe the RUNNING Theta Terminal: which API version is live (v2 on 25510 or v3 on 25503) and what does a
historical greeks/OI response look like? Run AFTER starting the Terminal; paste the output back so the GEX puller
endpoints get finalized exactly. Harmless read-only pings.

Run: backend/.venv/Scripts/python.exe experiments/options_signals_v0/theta_check.py
"""
from __future__ import annotations

import requests


def ping(name: str, url: str, params: dict) -> None:
    try:
        r = requests.get(url, params=params, timeout=10)
        body = r.text[:700]
        print(f"[{name}] HTTP {r.status_code}\n  {url}?{ '&'.join(f'{k}={v}' for k, v in params.items()) }\n  {body}\n")
    except Exception as e:  # noqa: BLE001
        print(f"[{name}] NO RESPONSE -- {str(e)[:160]}\n")


def main() -> int:
    print("Probing Theta Terminal (is it running + subscribed?)...\n")
    print("=== v2 API (port 25510) ===")
    ping("v2 expirations", "http://127.0.0.1:25510/v2/list/expirations", {"root": "SPXW"})
    ping("v2 bulk eod_greeks", "http://127.0.0.1:25510/v2/bulk_hist/option/eod_greeks",
         {"root": "SPXW", "exp": 20250620, "start_date": 20250609, "end_date": 20250610})
    ping("v2 bulk open_interest", "http://127.0.0.1:25510/v2/bulk_hist/option/open_interest",
         {"root": "SPXW", "exp": 20250620, "start_date": 20250609, "end_date": 20250610})
    print("=== v3 API (port 25503) ===")
    ping("v3 expirations", "http://127.0.0.1:25503/v3/option/list/expirations", {"symbol": "SPXW"})
    ping("v3 eod greeks (wildcard)", "http://127.0.0.1:25503/v3/option/history/eod_greeks",
         {"symbol": "SPXW", "expiration": "*", "strike": "*", "start_date": "2025-06-09", "end_date": "2025-06-10"})
    print("Paste everything above back to me -- whichever block returns real data tells me the exact endpoints to lock in.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
