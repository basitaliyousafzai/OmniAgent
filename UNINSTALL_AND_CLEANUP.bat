@echo off
setlocal
title OmniAgent OS - Complete Forceful Cleanup & Uninstall Suite
cd /d "%~dp0"

echo =====================================================================
echo         OmniAgent OS: Complete Uninstall & Zero-Pollution Suite
echo =====================================================================
echo.
echo WARNING: This script will:
echo   1. Forcefully kill any running OmniAgent processes (uvicorn, node, python).
echo   2. Delete local virtual environment (.venv) and runtime (.runtime).
echo   3. Delete local frontend dependencies (frontend\node_modules) and build (dist).
echo   4. Delete local caches (.cache, pip, npm, huggingface models).
echo   5. Delete runtime data, audit logs, screenshots, and .env.local secrets.
echo   6. Delete all Python __pycache__ folders.
echo.
echo Your computer will be left 100%% CLEAN with zero residual CPU/RAM or disk overhead.
echo.
set /p CONFIRM="Are you sure you want to proceed with complete uninstallation? (Y/N): "
if /i not "%CONFIRM%"=="Y" (
    echo [*] Uninstallation aborted by user.
    pause
    exit /b 0
)

echo.
echo [1/6] Terminating active processes...
:: Kill by ports 8000 and 3000
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8000 ^| findstr LISTENING') do (
    taskkill /F /PID %%a >nul 2>&1
)
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :3000 ^| findstr LISTENING') do (
    taskkill /F /PID %%a >nul 2>&1
)
:: Kill background console windows
taskkill /FI "WINDOWTITLE eq OmniAgent Backend (FastAPI)*" /T /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq OmniAgent Frontend (Vite)*" /T /F >nul 2>&1

:: Kill python processes originating from our .venv
wmic process where "ExecutablePath like '%%%~dp0.venv%%%'" call terminate >nul 2>&1
wmic process where "ExecutablePath like '%%%~dp0.runtime%%%'" call terminate >nul 2>&1

echo [2/6] Removing local Python environments (.venv and .runtime)...
if exist ".venv" (
    rmdir /s /q ".venv" >nul 2>&1
    echo   - Removed .venv/
)
if exist ".runtime" (
    rmdir /s /q ".runtime" >nul 2>&1
    echo   - Removed .runtime/
)

echo [3/6] Removing local frontend dependencies and build cache...
if exist "frontend\node_modules" (
    rmdir /s /q "frontend\node_modules" >nul 2>&1
    echo   - Removed frontend\node_modules/
)
if exist "frontend\dist" (
    rmdir /s /q "frontend\dist" >nul 2>&1
    echo   - Removed frontend\dist/
)
if exist "frontend\.vite" (
    rmdir /s /q "frontend\.vite" >nul 2>&1
    echo   - Removed frontend\.vite/
)

echo [4/6] Removing local package caches (.cache: pip, npm, whisper models)...
if exist ".cache" (
    rmdir /s /q ".cache" >nul 2>&1
    echo   - Removed .cache/
)

echo [5/6] Removing runtime data, screenshots, logs, and stored API keys...
if exist ".omniagent_data" (
    rmdir /s /q ".omniagent_data" >nul 2>&1
    echo   - Removed .omniagent_data/
)
if exist "workspace_audit.log" (
    del /f /q "workspace_audit.log*" >nul 2>&1
    echo   - Removed workspace_audit.log
)
if exist ".env.local" (
    del /f /q ".env.local" >nul 2>&1
    echo   - Removed .env.local
)

echo [6/6] Cleaning Python __pycache__ directories...
for /d /r . %%d in (__pycache__) do (
    if exist "%%d" rmdir /s /q "%%d" >nul 2>&1
)

echo.
echo =====================================================================
echo  SUCCESS: OmniAgent OS has been 100%% cleanly uninstalled!
echo  No global registry entries, system files, or background tasks remain.
echo =====================================================================
echo.
pause
