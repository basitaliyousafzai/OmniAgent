@echo off
setlocal enabledelayedexpansion

:: ============================================================================
:: OmniAgent YouTube Automator — Daily Autonomous Batch Bootstrapper
:: Module 10.1: Environment & CLI Bootstrapper
:: ============================================================================

set SCRIPT_DIR=%~dp0
set REPO_ROOT=%SCRIPT_DIR%..
cd /d "%REPO_ROOT%"

echo [OmniAgent] Launching YouTube Autonomous Pipeline...

:: Find Python Interpreter
set PYTHON_CMD=python
if exist "%REPO_ROOT%\.venv\Scripts\python.exe" (
    set PYTHON_CMD="%REPO_ROOT%\.venv\Scripts\python.exe"
) else if exist "%REPO_ROOT%\venv\Scripts\python.exe" (
    set PYTHON_CMD="%REPO_ROOT%\venv\Scripts\python.exe"
)

:: Run Orchestrator with any passed CLI flags
%PYTHON_CMD% "%REPO_ROOT%\modules\youtube_automator\orchestrator.py" %*

set EXIT_CODE=%ERRORLEVEL%
if %EXIT_CODE% EQU 0 (
    echo [OmniAgent] Pipeline completed successfully.
) else (
    echo [OmniAgent] Pipeline finished with exit code %EXIT_CODE%.
)

exit /b %EXIT_CODE%
