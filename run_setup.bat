@echo off
setlocal enabledelayedexpansion
title OmniAgent OS - Launcher
cd /d "%~dp0"

echo =====================================================================
echo           OmniAgent OS: Autonomous Desktop Workspace Launcher
echo =====================================================================
echo.

:: 1. Check or Bootstrap Local Python Environment (.venv)
if exist ".venv\Scripts\python.exe" (
    echo [*] Found local Python virtual environment in .venv
) else (
    echo [*] Local virtual environment not found. Checking portable runtime...
    if not exist ".runtime\python\python.exe" (
        echo [*] Downloading portable isolated CPython 3.11...
        if not exist ".runtime" mkdir .runtime
        powershell -NoProfile -Command "Invoke-WebRequest -Uri 'https://github.com/astral-sh/python-build-standalone/releases/download/20241016/cpython-3.11.10%%2B20241016-x86_64-pc-windows-msvc-install_only.tar.gz' -OutFile '.runtime\python.tar.gz' -UseBasicParsing"
        echo [*] Extracting Python runtime...
        tar -xzf .runtime\python.tar.gz -C .runtime
        del /f /q .runtime\python.tar.gz >nul 2>&1
    )
    
    echo [*] Creating isolated virtual environment in .venv...
    .\.runtime\python\python.exe -m venv .venv
    echo [*] Installing backend dependencies into .venv...
    set "PIP_CACHE_DIR=%CD%\.cache\pip"
    .\.venv\Scripts\python.exe -m pip install --upgrade pip
    .\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
)

:: 2. Check and Install Frontend Node Modules
if not exist "frontend\node_modules" (
    echo [*] Installing local frontend node modules...
    cd frontend
    call npm.cmd install --cache "..\.cache\npm"
    cd ..
)

:: 3. Launch OmniAgent OS in 100% Native Desktop Window Application Mode
echo.
echo =====================================================================
echo  Launching OmniAgent OS Native Desktop Application...
echo  - Core Engine: Google Gemini (gemini-3.5-flash)
echo  - Window Mode: Native OS Desktop Application (Zero Browser Chrome)
echo  - Safety Kill Switch: Press Ctrl+Esc anytime to abort automation
echo  - To Stop: Close the desktop app window or run STOP_OMNIAGENT.bat
echo =====================================================================
echo.

.\.venv\Scripts\python.exe desktop_app.py

if errorlevel 1 (
    echo.
    echo [!] OmniAgent OS exited with code %ERRORLEVEL%.
)
echo.
echo [*] OmniAgent OS session ended.
pause


