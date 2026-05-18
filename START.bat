@echo off
setlocal
title Product Center Dashboard

cd /d "%~dp0"

set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"
set "PYTHONUNBUFFERED=1"

where python >nul 2>nul
if errorlevel 1 (
    echo Python was not found. Please install Python or add it to PATH.
    pause
    exit /b 1
)

echo Starting Product Center Dashboard...
echo A browser window should open automatically.
echo If it does not, use the URL printed below.
echo.

python "%~dp0dashboard.py" --open %*
set "exit_code=%ERRORLEVEL%"

echo.
echo Dashboard stopped. Exit code: %exit_code%
pause
exit /b %exit_code%
