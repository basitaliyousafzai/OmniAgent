@echo off
setlocal
title Stop OmniAgent OS Services
cd /d "%~dp0"

echo =====================================================================
echo                 Stopping OmniAgent OS Services
echo =====================================================================
echo.

echo [*] Terminating OmniAgent backend (port 8000)...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8000 ^| findstr LISTENING') do (
    taskkill /F /PID %%a >nul 2>&1
)

echo [*] Terminating OmniAgent frontend (port 3000)...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :3000 ^| findstr LISTENING') do (
    taskkill /F /PID %%a >nul 2>&1
)

:: Terminate cmd windows with matching titles
taskkill /FI "WINDOWTITLE eq OmniAgent Backend (FastAPI)*" /T /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq OmniAgent Frontend (Vite)*" /T /F >nul 2>&1

echo.
echo [*] OmniAgent services have been stopped.
echo.
pause
