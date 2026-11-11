@echo off
setlocal enabledelayedexpansion
set "PATH=%LOCALAPPDATA%\Programs\MinGit\cmd;%PATH%"

echo ===================================================================
echo   StockAI Pulse (AlgoScan) - Push to GitHub (Private Repo)
echo ===================================================================
echo.
echo Target Repository: https://github.com/komminenivenkatesh/StockAI_Pulse (Private)
echo.
echo NOTE: Since August 2021, GitHub requires a Personal Access Token (PAT)
echo       instead of your account password to push code.
echo.
echo If you don't have a token yet:
echo 1. Open: https://github.com/settings/tokens/new
echo 2. Give it a Note (e.g. StockAI)
echo 3. Check the "repo" scope (Full control of private repositories)
echo 4. Click "Generate token" and copy it (starts with ghp_...)
echo.
echo ===================================================================
set /p "GITHUB_TOKEN=Paste your GitHub Personal Access Token: "

if "%GITHUB_TOKEN%"=="" (
    echo [ERROR] Token cannot be empty. Please run this file again and paste your token.
    pause
    exit /b 1
)

echo.
echo Pushing latest code and description to main branch...
git push https://komminenivenkatesh:%GITHUB_TOKEN%@github.com/komminenivenkatesh/StockAI_Pulse.git main --force

if %ERRORLEVEL% equ 0 (
    echo.
    echo ===================================================================
    echo [SUCCESS] StockAI Pulse has been pushed to GitHub successfully!
    echo Refresh https://github.com/komminenivenkatesh/StockAI_Pulse to see it.
    echo ===================================================================
) else (
    echo.
    echo [FAILED] Push failed. Please check that:
    echo 1. Your token has the 'repo' scope checked.
    echo 2. Your token has not expired.
)

echo.
pause
