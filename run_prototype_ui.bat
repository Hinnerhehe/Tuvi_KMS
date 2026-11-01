@echo off
title KMS Tu Vi - Streamlit Web App
echo ========================================================
echo        KMS TU VI - GIAO DIEN STREAMLIT
echo ========================================================
echo.
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo [ERROR] Khong tim thay moi truong ao .venv!
    pause
    exit /b 1
)

echo Dang khoi chay Streamlit Web App...
echo Dia chi truy cap: http://localhost:8501
echo.
set PYTHONIOENCODING=utf-8
.venv\Scripts\python.exe -m streamlit run frontend\lasoban.py

pause
