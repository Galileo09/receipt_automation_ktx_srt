@echo off
cd /d "%~dp0"

echo.
echo ============================================
echo  Receipt Automation Dashboard
echo ============================================
echo.

set VENV_DIR=%~dp0.venv
set VENV_PYTHON=%VENV_DIR%\Scripts\python.exe
set VENV_PIP=%VENV_DIR%\Scripts\pip.exe
set VENV_PLAYWRIGHT=%VENV_DIR%\Scripts\playwright.exe

if not exist "%VENV_PYTHON%" (
    echo [venv not found] Creating virtual environment with uv...
    uv venv "%VENV_DIR%"
    if errorlevel 1 (
        echo [ERROR] Failed to create venv. Make sure uv is installed.
        pause
        exit /b 1
    )
    echo [venv created] %VENV_DIR%
    echo.
)

echo Installing / verifying required packages...
uv pip install --python "%VENV_PYTHON%" -r requirements.txt
echo.
echo Installing Playwright browser...
"%VENV_PLAYWRIGHT%" install chromium
echo.

echo Server: http://localhost:8300
echo Press Ctrl+C to stop.
echo.
cd web_ui

start "" /b cmd /c "timeout /t 2 >nul && start http://localhost:8300"

"%VENV_PYTHON%" -m uvicorn main:app --port 8300

pause
