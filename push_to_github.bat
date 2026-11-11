@echo off
set "PATH=%LOCALAPPDATA%\Programs\MinGit\cmd;%PATH%"
echo ===================================================
echo   StockAI Pulse (AlgoScan) - Push to GitHub
echo ===================================================
echo.
echo Pushing commit to: https://github.com/komminenivenkatesh/StockAI_Pulse.git
echo.
echo If prompted, enter your GitHub Username and Personal Access Token (or password).
echo.
git push -u origin main
echo.
if %ERRORLEVEL% equ 0 (
    echo [SUCCESS] Code and description pushed to GitHub successfully!
) else (
    echo [NOTE] If you saw 404 or authentication failed:
    echo 1. Create the repository at https://github.com/new with name: StockAI_Pulse
    echo 2. Generate a Personal Access Token at https://github.com/settings/tokens (repo scope)
    echo 3. Run this file again.
)
echo.
pause
