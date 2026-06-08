@echo off
setlocal
REM BacktestStation launcher -- backend + status page only (no frontend SPA).
REM Serves the read-only status dashboard at http://127.0.0.1:8000
cd /d "%~dp0"

if not exist "backend\.venv\Scripts\activate.bat" (
  echo.
  echo [start.bat] Backend venv not found at backend\.venv
  echo [start.bat] Create it once with:
  echo     cd backend
  echo     python -m venv .venv
  echo     .venv\Scripts\python -m pip install -e ".[dev]"
  echo.
  exit /b 1
)

call backend\.venv\Scripts\activate.bat
if errorlevel 1 (
  echo [start.bat] Failed to activate venv at backend\.venv
  exit /b 1
)

cd backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000

endlocal
