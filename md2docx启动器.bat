@echo off
chcp 936 >nul 2>&1
title MD2DOCX - Markdown Batch to DOCX Converter
color 0B
echo.
echo   ============================================================
echo              MD2DOCX  Markdown Batch to DOCX Tool
echo                         Version 1.0
echo   ====================================================
echo.

cd /d "%~dp0"

set PORT=9473

echo [Step 1/4] Checking port %PORT%...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":%PORT% " ^| findstr "LISTENING"') do (
    echo    Port %PORT% is occupied by PID %%a, terminating...
    taskkill /PID %%a /F >nul 2>&1
    timeout /t 1 /nobreak >nul
)
echo    Port %PORT% is ready.
echo.

echo [Step 2/4] Checking Python dependencies...
python -c "import flask; import docx; import markdown" 2>nul
if errorlevel 1 (
    echo    Installing dependencies...
    pip install -r requirements.txt -q
) else (
    echo    All dependencies OK.
)
echo.

echo [Step 3/4] Starting Flask server on http://127.0.0.1:%PORT%...
start "" http://127.0.0.1:%PORT%
python app.py
if errorlevel 1 (
    echo.
    echo   [ERROR] Server failed to start!
    echo   Press any key to exit...
    pause >nul
    exit /b 1
)
