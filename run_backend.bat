@echo off
title KMS Tu Vi - FastAPI Server
cd /d "%~dp0"

echo ========================================================
echo        KMS TU VI - KHOI DONG HE THONG BACKEND
echo ========================================================
echo.

if not exist ".venv\Scripts\python.exe" (
    echo [ERROR] Khong tim thay moi truong ao tai: %~dp0.venv\Scripts\python.exe
    echo Vui long kiem tra thu muc du an.
    echo.
    pause
    exit /b 1
)

set PYTHONIOENCODING=utf-8
.venv\Scripts\python.exe run_server.py

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [LUA Y] Server da dung hoac gap su co (Ma loi: %ERRORLEVEL%).
    pause
)
