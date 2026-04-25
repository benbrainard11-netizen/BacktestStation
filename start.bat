@echo off
setlocal

REM One-click launcher for BacktestStation.
REM Runs the Tauri desktop shell which spawns Next.js dev (port 3000)
REM and the FastAPI backend sidecar on uvicorn (port 8000).

REM Operate from the directory containing this file regardless of cwd.
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

if not exist "frontend\node_modules" (
  echo.
  echo [start.bat] Frontend node_modules missing. Run once:
  echo     cd frontend
  echo     npm install
  echo.
  exit /b 1
)

call backend\.venv\Scripts\activate.bat
if errorlevel 1 (
  echo [start.bat] Failed to activate venv at backend\.venv
  exit /b 1
)

cd frontend
npm run tauri:dev

endlocal
