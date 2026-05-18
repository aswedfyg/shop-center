@echo off
cd /d "%~dp0.."
set PYTHONUTF8=1
python "%CD%\dashboard\app.py" --open %*
