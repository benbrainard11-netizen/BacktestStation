@echo off
REM Daily autonomous PAPER cycle. Scheduled pre-open. Logs to out\auto_paper.log.
cd /d C:\Users\benbr\BacktestStation
backend\.venv\Scripts\python.exe -u experiments\stock_strategies_v0\unified_v0\auto_paper.py --live --equity 10000
