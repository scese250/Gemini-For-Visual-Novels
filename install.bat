@echo off
title Gemini Hybrid Server Installer
cls
echo ===================================================
echo   GEMINI HYBRID SERVER - INSTALLATION
echo ===================================================
echo.

REM 1. Verify Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python not detected. Please install Python and add it to your PATH.
    pause
    exit /b
)

REM 2. Create VENV
if not exist "venv" (
    echo [Creating VENV] Creating virtual environment...
    python -m venv venv
)

REM 3. Activate VENV
call venv\Scripts\activate.bat

REM 4. Update PIP and Install Dependencies
echo [Installing Options] Updating pip and installing libraries...
python -m pip install --upgrade pip
pip install -r requirements.txt

echo.
echo ===================================================
echo   INSTALLATION COMPLETE
echo ===================================================
echo Now execute 'run.bat' to start the server.
echo.
pause
