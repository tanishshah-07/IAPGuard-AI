@echo off
cd /d "%~dp0backend" || goto :failed
if not exist ".venv\Scripts\python.exe" (
    python -m venv .venv || py -m venv .venv || goto :failed
)
".venv\Scripts\python.exe" -m pip install -r requirements.txt || goto :failed
".venv\Scripts\python.exe" -m uvicorn app.main:app --reload || goto :failed
exit /b 0

:failed
echo Backend startup failed. Check the error above.
pause
exit /b 1
