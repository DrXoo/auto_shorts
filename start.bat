@echo off
echo ============================================
echo   AutoShorts Web Interface
echo ============================================
echo.

:: Check for Python venv
if not exist ".venv\Scripts\activate.bat" (
    echo ERROR: Python virtual environment not found at .venv\
    echo Run: python -m venv .venv
    pause
    exit /b 1
)

:: Check for node_modules
if not exist "frontend\node_modules" (
    echo Installing frontend dependencies...
    cd frontend
    call npm install
    cd ..
)

echo Starting backend (FastAPI) on http://localhost:8000 ...
start "AutoShorts Backend" cmd /k "call .venv\Scripts\activate.bat && cd /d %~dp0 && python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload"

echo Starting frontend (Next.js) on http://localhost:3000 ...
start "AutoShorts Frontend" cmd /k "cd /d %~dp0\frontend && npm run dev"

timeout /t 4 /nobreak > nul

echo.
echo ============================================
echo   Backend:  http://localhost:8000
echo   Frontend: http://localhost:3000
echo   API Docs: http://localhost:8000/docs
echo ============================================
echo.
echo Both servers are running in separate windows.
echo Close those windows to stop the servers.
echo.
pause
