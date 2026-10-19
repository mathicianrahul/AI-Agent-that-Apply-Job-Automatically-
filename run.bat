@echo off
setlocal enabledelayedexpansion

echo ===================================================
echo        JobPilot AI - One-Click Launcher
echo ===================================================

:: 1. Check Python installation
where python >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Python is not installed or not in PATH!
    echo Please install Python 3.11 or higher from https://python.org
    pause
    exit /b 1
)

:: 2. Check and create virtual environment if not present
if not exist "venv\Scripts\activate.bat" (
    echo [INFO] Creating Python virtual environment (venv)...
    python -m venv venv
    if %ERRORLEVEL% NEQ 0 (
        echo [ERROR] Failed to create virtual environment.
        pause
        exit /b 1
    )
)

:: 3. Activate virtual environment
call venv\Scripts\activate.bat

:: 4. Ensure .env exists
if not exist ".env" (
    if exist ".env.example" (
        echo [INFO] Creating .env from .env.example...
        copy .env.example .env >nul
    )
)

:: 5. Install or update dependencies
echo [INFO] Checking dependencies in requirements.txt...
pip install -r requirements.txt --quiet

:: 6. Launch Streamlit Application
echo ===================================================
echo [SUCCESS] Starting JobPilot AI Dashboard...
echo Open your browser to http://localhost:8501
echo ===================================================
streamlit run app.py

pause
