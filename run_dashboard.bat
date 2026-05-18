@echo off
cd /d "%~dp0"
set PYTHONUTF8=1
python "%~dp0dashboard.py" --open %*
