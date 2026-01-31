@echo off
REM Launch Project Dashboard System Tray
REM This keeps the console visible for debugging

cd /d "%~dp0"
uv run --project backend python backend/tray.py
pause
