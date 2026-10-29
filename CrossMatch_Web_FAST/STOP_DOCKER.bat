@echo off
setlocal
cd /d "%~dp0"
echo Stop CrossMatch only. Uploaded files, results and accounts are retained.
echo Wait for processing to finish before stopping; running jobs may be interrupted.
choice /C YN /N /M "Stop CrossMatch now? [Y/N] "
if errorlevel 2 exit /b 0
where powershell.exe >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Windows PowerShell 5.1 is required on Windows 11.
    pause
    exit /b 1
)
powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File "%~dp0CROSSMATCH_DOCKER_CONTROL.ps1" -Action Stop
set "RESULT=%ERRORLEVEL%"
if not "%RESULT%"=="0" (
    echo.
    echo CrossMatch state could not be confirmed. No volumes were deleted.
    pause
    exit /b %RESULT%
)
echo.
echo CrossMatch shutdown check completed.
pause
exit /b 0
