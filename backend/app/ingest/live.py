"""Databento Live TBBO ingester.

Streams TBBO records (top of book + trades) for a configured set of
CME futures symbols and appends them to a per-day DBN file. Writes a
heartbeat JSON so BacktestStation's /monitor page can show live feed
status. Reconnects with exponential backoff on session failure.

Run on the 24/7 collection node (currently insyncserver / ben-247):

    set DATABENTO_API_KEY=db-...
    python -m app.ingest.live

Stop with Ctrl+C. Logs to {DATA_ROOT}/logs/live_ingester.log.

Environment variables:
    DATABENTO_API_KEY   required. The Live API key from databento.com.
    BS_DATA_ROOT        optional. Default C:\\data on Windows, ./data
                        elsewhere. Where DBN files + heartbeat live.

Output layout:
    {DATA_ROOT}/raw/live/{DATASET}-{SCHEMA}-{YYYY-MM-DD}.dbn
    {DATA_ROOT}/heartbeat/live_ingester.json
    {DATA_ROOT}/logs/live_ingester.log

Restart safety:
    If the script crashes mid-day and is restarted, it appends to the
    existing DBN file for that UTC date. No data lost; some duplication
    possible across the restart boundary (Databento's reconnect logic
    handles most of this). Downstream parquet conversion can dedup.
"""

from __future__ import annotations

import datetime as dt
import json
import logging
import os
import signal
import sys
import threading
import time
from pathlib import Path
from typing import Any

try:
    import databento as db
except ImportError:  # pragma: no cover
    sys.stderr.write(
        "databento package not installed. Run: pip install databento\n"
    )
    sys.exit(1)


# --- Configuration -------------------------------------------------------

API_KEY = os.environ.get("DATABENTO_API_KEY")
DATA_ROOT = Path(
    os.environ.get(
        "BS_DATA_ROOT",
        "C:/data" if os.name == "nt" else "./data",
    )
)

LIVE_DIR = DATA_ROOT / "raw" / "live"
HEARTBEAT_DIR = DATA_ROOT / "heartbeat"
LOG_DIR = DATA_ROOT / "logs"
HEARTBEAT_FILE = HEARTBEAT_DIR / "live_ingester.json"
LOG_FILE = LOG_DIR / "live_ingester.log"

# CME Globex MDP3 — the dataset code for ES/NQ/YM/RTY top-of-book.
DATASET = "GLBX.MDP3"
SCHEMA = "tbbo"

# Continuous front-month parent symbology — auto-rolls when contracts
# expire so we don't have to maintain a rollover schedule.
SYMBOLS = ["NQ.c.0", "ES.c.0", "YM.c.0", "RTY.c.0"]
STYPE_IN = "continuous"

HEARTBEAT_INTERVAL_SEC = 10
RECONNECT_BACKOFF_SEC = [5, 15, 30, 60, 120, 300]


# --- Logging -------------------------------------------------------------


def setup_logging() -> logging.Logger:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("live_ingester")
    logger.setLevel(logging.INFO)
    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")

    file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
    file_handler.setFormatter(fmt)
    logger.addHandler(file_handler)

    # Mirror to stderr so interactive runs see what's happening.
    stream_handler = logging.StreamHandler(sys.stderr)
    stream_handler.setFormatter(fmt)
    logger.addHandler(stream_handler)
    return logger


# --- Runtime state -------------------------------------------------------


class IngesterState:
    """Thread-safe counters + status for the heartbeat writer."""

    def __init__(self) -> None:
        self.started_at = dt.datetime.now(dt.timezone.utc)
        self.ticks_received = 0
        self.last_tick_ts: dt.datetime | None = None
        self.current_file: Path | None = None
        self.current_date: dt.date | None = None
        self.last_error: str | None = None
        self.reconnect_count = 0
        # RLock (not Lock) because status_json() acquires the lock and then
        # calls ticks_last_60s() which tries to acquire it again. A regular
        # Lock would deadlock the heartbeat thread on its first write -- it
        # would hang silently with no log entry, and the heartbeat file
        # would never be created.
        self._lock = threading.RLock()
        self._tick_window: list[float] = []  # epoch seconds of recent ticks

    def record_tick(self) -> None:
        now = time.time()
        with self._lock:
            self.ticks_received += 1
            self.last_tick_ts = dt.datetime.now(dt.timezone.utc)
            self._tick_window.append(now)
            cutoff = now - 60
            # Drop ticks older than 60s, keeping the buffer small.
            while self._tick_window and self._tick_window[0] < cutoff:
                self._tick_window.pop(0)

    def ticks_last_60s(self) -> int:
        with self._lock:
            cutoff = time.time() - 60
            return sum(1 for t in self._tick_window if t >= cutoff)

    def status_json(self) -> dict[str, Any]:
        with self._lock:
            now = dt.datetime.now(dt.timezone.utc)
            return {
                "status": "error" if self.last_error else "running",
                "started_at": self.started_at.isoformat(timespec="seconds"),
                "uptime_seconds": int(
                    (now - self.started_at).total_seconds()
                ),
                "last_tick_ts": (
                    self.last_tick_ts.isoformat(timespec="seconds")
                    if self.last_tick_ts
                    else None
                ),
                "ticks_received": self.ticks_received,
                "ticks_last_60s": self.ticks_last_60s(),
                "current_file": (
                    str(self.current_file) if self.current_file else None
                ),
                "current_date": (
                    self.current_date.isoformat()
                    if self.current_date
                    else None
                ),
                "symbols": SYMBOLS,
                "dataset": DATASET,
                "schema": SCHEMA,
                "stype_in": STYPE_IN,
                "reconnect_count": self.reconnect_count,
                "last_error": self.last_error,
            }


# --- Heartbeat writer ----------------------------------------------------


def heartbeat_loop(
    state: IngesterState, stop: threading.Event, logger: logging.Logger
) -> None:
    HEARTBEAT_DIR.mkdir(parents=True, exist_ok=True)
    while not stop.is_set():
        try:
            tmp = HEARTBEAT_FILE.with_suffix(".tmp")
            payload = state.status_json()
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2)
            tmp.replace(HEARTBEAT_FILE)  # atomic rename
        except Exception as e:
            logger.warning(f"heartbeat write failed: {e}")
        stop.wait(HEARTBEAT_INTERVAL_SEC)


# --- Ingest session ------------------------------------------------------


def file_for_date(d: dt.date) -> Path:
    return LIVE_DIR / f"{DATASET}-{SCHEMA}-{d.isoformat()}.dbn"


def run_session(
    state: IngesterState, stop: threading.Event, logger: logging.Logger
) -> None:
    """One Databento Live session. Runs until day rolls over or stop is set.

    Raises on connection error so the outer loop can handle backoff.
    """
    LIVE_DIR.mkdir(parents=True, exist_ok=True)

    today = dt.datetime.now(dt.timezone.utc).date()
    out_path = file_for_date(today)
    state.current_file = out_path
    state.current_date = today

    logger.info(
        f"opening session: dataset={DATASET} schema={SCHEMA} "
        f"symbols={SYMBOLS} -> {out_path}"
    )

    client = db.Live(key=API_KEY)
    client.subscribe(
        dataset=DATASET,
        schema=SCHEMA,
        symbols=SYMBOLS,
        stype_in=STYPE_IN,
    )

    # Append mode is critical for restart safety. Multiple add_stream
    # calls would write twice; we use one.
    out_handle = open(out_path, "ab")
    client.add_stream(out_handle)

    def on_record(record: Any) -> None:  # noqa: ANN401
        state.record_tick()

    client.add_callback(on_record)
    client.start()
    state.last_error = None
    logger.info("session started")

    try:
        # The Live client streams asynchronously; this loop just watches
        # for day rollover or operator stop. Disconnect detection is
        # delegated to Databento's internal reconnect logic; if that
        # fails the heartbeat will go stale and we'll notice externally.
        while not stop.is_set():
            now_date = dt.datetime.now(dt.timezone.utc).date()
            if now_date != today:
                logger.info(
                    f"UTC date rolled {today} -> {now_date}; rotating file"
                )
                break
            time.sleep(1)
    finally:
        try:
            client.stop()
        except Exception as e:
            logger.warning(f"client.stop() raised: {e}")
        try:
            out_handle.close()
        except Exception:
            pass
        logger.info(
            f"session closed; ticks_received={state.ticks_received}"
        )


# --- Entry point ---------------------------------------------------------


def main() -> int:
    if not API_KEY:
        sys.stderr.write("DATABENTO_API_KEY env var not set\n")
        return 1

    logger = setup_logging()
    logger.info(f"starting live ingester; data root={DATA_ROOT}")

    state = IngesterState()
    stop = threading.Event()

    def handle_signal(signum: int, frame: Any) -> None:  # noqa: ANN401
        logger.info(f"signal {signum} received; shutting down")
        stop.set()

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)
    if hasattr(signal, "SIGBREAK"):
        signal.signal(signal.SIGBREAK, handle_signal)

    hb_thread = threading.Thread(
        target=heartbeat_loop,
        args=(state, stop, logger),
        daemon=True,
        name="heartbeat",
    )
    hb_thread.start()

    backoff_idx = 0
    while not stop.is_set():
        try:
            run_session(state, stop, logger)
            # Clean rollover or stop — reset backoff for next session.
            backoff_idx = 0
        except Exception as e:
            state.last_error = f"{type(e).__name__}: {e}"
            state.reconnect_count += 1
            wait = RECONNECT_BACKOFF_SEC[
                min(backoff_idx, len(RECONNECT_BACKOFF_SEC) - 1)
            ]
            logger.error(
                f"session failed: {state.last_error}. retrying in {wait}s"
            )
            backoff_idx += 1
            stop.wait(wait)

    logger.info("ingester exited cleanly")
    return 0


if __name__ == "__main__":
    sys.exit(main())
