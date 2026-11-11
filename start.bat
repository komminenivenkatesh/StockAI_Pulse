@echo off
setlocal

echo =========================================
echo       AlgoScan / StockAI Pulse
echo =========================================

:: Check if Docker is running
docker info >nul 2>&1
if %errorlevel% equ 0 (
    echo Docker is running.
    set /p use_docker="Do you want to run with Docker Compose? (y/n): "
    if /i "%use_docker%"=="y" (
        echo Starting Docker Compose...
        docker compose up --build
        goto :EOF
    )
) else (
    echo Docker is not running or not installed. Falling back to local setup.
)

:: Check if .env exists
if not exist "backend\.env" (
    if exist "backend\.env.example" (
        echo Copying backend\.env.example to backend\.env
        copy "backend\.env.example" "backend\.env"
    )
)

:: Check if .venv exists, otherwise check for installed Python 3.11
set "PY_CMD="
if exist "backend\.venv\Scripts\python.exe" (
    set "PY_CMD=backend\.venv\Scripts\python.exe"
) else if exist "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" (
    set "PY_CMD=%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
) else (
    set "PY_CMD=python"
)

echo.
echo [1/3] Starting Backend...
start "AlgoScan Backend" cmd /c "cd backend && ..\%PY_CMD% -m uvicorn app.main:app --reload --port 8000"

echo [2/3] Waiting for backend to be ready...
:wait_loop
timeout /t 1 /nobreak >nul
curl.exe -s -o nul -w "%%{http_code}" http://localhost:8000/health | findstr "200" >nul 2>&1
if %errorlevel% neq 0 (
    echo        Waiting for backend...
    goto :wait_loop
)
echo        Backend is ready!

echo [3/3] Starting Frontend...
start "AlgoScan Frontend" cmd /c "cd frontend && npm run dev"

timeout /t 3 /nobreak >nul

echo.
echo Opening browser...
start http://localhost:5173

echo.
echo =========================================
echo   All services running! No errors.
echo   Backend:  http://localhost:8000
echo   Frontend: http://localhost:5173
echo =========================================
echo.
echo Keep the backend and frontend windows open.
pause
