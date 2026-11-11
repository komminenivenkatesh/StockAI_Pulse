@echo off
setlocal

echo =======================================================
echo    AlgoScan / StockAI Pulse - Official Ngrok Tunnel
echo =======================================================
echo.

set "PYTHON_EXE=python"
where python >nul 2>&1
if %errorlevel% neq 0 (
    set "PYTHON_EXE=C:\Users\DELL\AppData\Local\Programs\Python\Python311\python.exe"
)

"%PYTHON_EXE%" "%~dp0ngrok_tunnel.py"
pause
