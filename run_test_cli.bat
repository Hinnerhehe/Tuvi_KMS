@echo off
title KMS Tu Vi - Interactive Horoscope CLI
echo ========================================================
echo        KMS TU VI - LUAN GIAI TU VI AI (TERMINAL)
echo ========================================================
echo.
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo [ERROR] Khong tim thay moi truong ao .venv!
    pause
    exit /b 1
)

set PYTHONIOENCODING=utf-8
.venv\Scripts\python.exe scripts\test_horoscope_cli.py -i

echo.
echo ========================================================
echo Nhan phim bat ky de thoat...
pause > nul
