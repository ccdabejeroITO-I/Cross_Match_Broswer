@echo off
setlocal
cd /d "%~dp0"
rem CrossMatch v6.32.74: diagnostics and safe Docker Desktop launch live in PowerShell helper.
where powershell.exe >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Windows PowerShell 5.1 is required on Windows 11.
    pause
    exit /b 1
)
rem Start action must be interactive to confirm an upgrade safely.
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0CROSSMATCH_DOCKER_CONTROL.ps1" -Action Start
set "RESULT=%ERRORLEVEL%"
if not "%RESULT%"=="0" (
    echo.
    echo CrossMatch did not start. Review the specific error above.
    pause
    exit /b %RESULT%
)
rem Preserve original behavior: open the application after verified health.
call "%~dp0OPEN_APP.bat"
set "RESULT=%ERRORLEVEL%"
if not "%RESULT%"=="0" (
    echo [WARNING] CrossMatch started, but the browser could not be opened.
    echo Open http://127.0.0.1:18090/ or your configured CROSSMATCH_HTTP_PORT manually.
    pause
)
exit /b %RESULT%
