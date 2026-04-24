"""Data ingestion processes — daemons that write to the warehouse.

Currently:
- live.py    Databento Live TBBO streamer for the 24/7 collection node.

Future:
- historical.py   Monthly cron-driven MBP-1 batch puller.
- parquet_mirror.py   Periodic DBN -> parquet conversion.
"""
