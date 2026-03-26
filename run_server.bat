@echo off
cd /d "%~dp0"

echo.
echo ============================================
echo  Receipt Automation Dashboard
echo ============================================
echo.

echo Installing / verifying required packages...
pip install -r requirements.txt
echo.
echo Installing Playwright browser...
playwright install chromium
echo.

echo Server: http://localhost:8000
echo Press Ctrl+C to stop.
echo.
cd web_ui

:: open browser after server starts (2 sec delay)
start "" /b cmd /c "timeout /t 2 >nul && start http://localhost:8000"

python -m uvicorn main:app --port 8000

pause
