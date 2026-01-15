@echo off
title Gemini Hybrid Server Runner
cls
echo ===================================================
echo   GEMINI HYBRID SERVER - STARTING...
echo ===================================================
echo.

REM 1. Verify VENV
if not exist "venv" (
    echo [ERROR] Virtual environment not found. Please run 'install.bat' first.
    pause
    exit /b
)

REM 2. Activate VENV
call venv\Scripts\activate.bat

REM 3. Run Server
python Gemini.py

pause
