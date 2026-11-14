@echo off
setlocal enabledelayedexpansion
set "PATH=%LOCALAPPDATA%\Programs\MinGit\cmd;%PATH%"

echo ===================================================================
echo   Push StockAI Pulse to chandinibattini2006-crypto/StockAI_Pulse
echo ===================================================================
echo.
echo Target: https://github.com/chandinibattini2006-crypto/StockAI_Pulse
echo.
echo NOTE: This computer's default Git credentials are set to 'komminenivenkatesh'.
echo       To push to 'chandinibattini2006-crypto', enter a Personal Access Token
echo       generated from the chandinibattini2006-crypto GitHub account.
echo.
echo 1. Open: https://github.com/settings/tokens/new (while logged in as chandinibattini2006-crypto)
echo 2. Note: StockAI, Scope: check [x] repo
echo 3. Generate token and copy it (starts with ghp_...)
echo ===================================================================
echo.
set /p "CHANDINI_TOKEN=Paste Token for chandinibattini2006-crypto: "

if "%CHANDINI_TOKEN%"=="" (
    echo [ERROR] Token cannot be empty.
    pause
    exit /b 1
)

echo.
echo Pushing latest code to chandinibattini2006-crypto/StockAI_Pulse...
git push https://chandinibattini2006-crypto:%CHANDINI_TOKEN%@github.com/chandinibattini2006-crypto/StockAI_Pulse.git main --force

if %ERRORLEVEL% equ 0 (
    echo.
    echo ===================================================================
    echo [SUCCESS] Code pushed successfully!
    echo View at: https://github.com/chandinibattini2006-crypto/StockAI_Pulse
    echo ===================================================================
) else (
    echo.
    echo [FAILED] Push failed. Please verify that the token has 'repo' scope.
)

echo.
pause
