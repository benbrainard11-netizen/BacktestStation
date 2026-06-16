"""Robust single-shard options puller — manages ITS OWN dedicated Terminal.

Multi-session proven 2026-06-13: this account allows concurrent Terminals on different
ports, so we run one Terminal per shard and pull in parallel for a real Nx speedup.
Each puller: talks to its own port, restarts ONLY its own Terminal (matched by config
file name) on a hang, fails fast (45s), skips genuinely-poison expirations, resumes
from the shared theta_store cache (cache keys include root+params, so parallel shards
never collide).

Args: INDEX START END [PORT] [CONFIG_PATH] [SHARD] [NSHARDS]
Run:  backend\\.venv\\Scripts\\python.exe robust_pull.py SPX 2021-01-01 2023-05-31 25511 C:\\...\\config_1.properties 1 3
"""
from __future__ import annotations

import os
import sys

_A = sys.argv
INDEX, START, END = _A[1], _A[2], _A[3]
PORT = _A[4] if len(_A) > 4 else "25510"
CONFIG = _A[5] if len(_A) > 5 else None
SHARD = int(_A[6]) if len(_A) > 6 else 0
NSHARDS = int(_A[7]) if len(_A) > 7 else 1
WINDOW = int(_A[8]) if len(_A) > 8 else 30   # request window days; lighter = fewer Terminal freezes
# main data endpoint: eod_greeks for SPX/RUT/DJX; "bulk_hist/option/eod" (raw prices) for NDX,
# which has no vendor greeks -> we compute IV/gamma from these prices downstream.
PRICE_EP = _A[9] if len(_A) > 9 else "bulk_hist/option/eod_greeks"
IVL = int(_A[10]) if len(_A) > 10 else 0     # intraday interval ms (e.g. 300000=5m); 0 = daily/EOD
os.environ["THETA_PORT"] = PORT           # theta_store reads this at import for BASE
os.environ["THETA_TIMEOUT"] = "150" if IVL else "45"  # intraday responses are huge -> need longer
os.environ["THETA_RETRIES"] = "1"

import subprocess  # noqa: E402
import time  # noqa: E402
from pathlib import Path  # noqa: E402

import pandas as pd  # noqa: E402
import requests  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
import theta_store as TS  # noqa: E402
from gex_pull import ROOT, _ymd  # noqa: E402

JAVA = r"C:\Program Files\Microsoft\jdk-21.0.11.10-hotspot\bin\java.exe"
TDIR = Path(__file__).resolve().parent / "theta"
JAR = str(TDIR / "ThetaTerminal.jar")
CREDS = str(TDIR / "creds.txt")
BASE = f"http://127.0.0.1:{PORT}/v2"
CFG_KEY = Path(CONFIG).stem if CONFIG else "config_0"   # match THIS terminal's java proc
MAX_RESTARTS = 3
OUTDIR = Path(__file__).resolve().parent / "out" / "_shards"
POISON = OUTDIR / f"poison_{INDEX.lower()}_s{SHARD}.txt"
DETACHED = 0x00000008 | 0x08000000


def term_ok() -> bool:
    try:
        return requests.get(f"{BASE}/list/expirations", params={"root": "SPXW"}, timeout=8).status_code == 200
    except Exception:
        return False


def restart_terminal() -> bool:
    # kill ONLY this shard's Terminal (matched by its config file name), then relaunch it
    subprocess.run(["powershell", "-NoProfile", "-Command",
                    f"Get-CimInstance Win32_Process -Filter \"Name='java.exe'\" | "
                    f"Where-Object {{ $_.CommandLine -like '*ThetaTerminal*' -and $_.CommandLine -like '*{CFG_KEY}*' }} | "
                    f"ForEach-Object {{ Stop-Process -Id $_.ProcessId -Force }}"], capture_output=True)
    time.sleep(4)
    args = [JAVA, "-jar", JAR]
    if CONFIG:
        args += ["--config", CONFIG]
    args += ["--creds-file", CREDS]
    subprocess.Popen(args, cwd=str(TDIR), creationflags=DETACHED)
    for _ in range(24):
        time.sleep(5)
        if term_ok():
            return True
    return False


def load_poison() -> set[int]:
    return {int(x) for x in POISON.read_text().split() if x.strip()} if POISON.exists() else set()


def main() -> int:
    root = ROOT.get(INDEX, INDEX)   # index key -> weekly root; else use INDEX literally (stock tickers)
    s, e = _ymd(START), _ymd(END)
    OUTDIR.mkdir(parents=True, exist_ok=True)
    if not term_ok():
        print(f"[{INDEX} s{SHARD} :{PORT}] terminal not serving -> starting", flush=True)
        restart_terminal()
    allexps = sorted((x for x in TS.expirations(root)
                      if s <= x <= _ymd(pd.Timestamp(END) + pd.Timedelta(days=90))), reverse=True)
    exps = allexps[SHARD::NSHARDS]
    poison = load_poison()
    print(f"[{INDEX} s{SHARD}/{NSHARDS} :{PORT}] {len(exps)} expirations (of {len(allexps)}); "
          f"{len(poison)} known-poison", flush=True)
    pulled = skipped = 0
    t0 = time.time()
    for i, exp in enumerate(exps):
        if exp in poison:
            skipped += 1
            continue
        exp_ts = pd.Timestamp(str(exp))
        s_k = max(s, _ymd(exp_ts - pd.Timedelta(days=WINDOW)))
        e_k = min(e, exp)
        if s_k > e_k:
            continue
        ok = False
        price_kw = {"ivl": IVL} if IVL else {}   # intraday endpoints take ivl; OI is always daily
        for attempt in range(MAX_RESTARTS + 1):
            try:
                TS.fetch(PRICE_EP, root=root, exp=exp, start_date=s_k, end_date=e_k, **price_kw)
                TS.fetch("bulk_hist/option/open_interest", root=root, exp=exp, start_date=s_k, end_date=e_k)
                ok = True
                break
            except Exception as ex:
                print(f"  [{INDEX} s{SHARD}] exp {exp} fail try {attempt}: {str(ex)[:45]} -> restart terminal", flush=True)
                restart_terminal()
        if ok:
            pulled += 1
        else:
            poison.add(exp)
            POISON.write_text("\n".join(map(str, sorted(poison))))
            skipped += 1
            print(f"  [{INDEX} s{SHARD}] exp {exp} POISON -> skipped", flush=True)
        if (i + 1) % 10 == 0:
            el = (time.time() - t0) / 60 + 1e-9
            print(f"  [{INDEX} s{SHARD}] {i+1}/{len(exps)}  pulled={pulled} skipped={skipped}  "
                  f"({pulled/el:.1f}/min)", flush=True)
    print(f"[{INDEX} s{SHARD}] DONE: pulled={pulled} skipped={skipped} of {len(exps)}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
