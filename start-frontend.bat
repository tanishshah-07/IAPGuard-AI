@echo off
cd /d "%~dp0frontend" || goto :failed
if not exist "node_modules\.bin\vite.cmd" (
    call npm ci || goto :failed
)
call npm run dev || goto :failed
exit /b 0

:failed
echo Frontend startup failed. Check the error above.
pause
exit /b 1
