"""Data ingestion processes — daemons that write to the warehouse.

Currently:
- live.py            Databento Live TBBO streamer for the 24/7 node.
- parquet_mirror.py  Periodic DBN -> per-symbol parquet conversion.

Future:
- historical.py   Monthly cron-driven MBP-1 batch puller.
"""
