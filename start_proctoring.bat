@echo off
title PROCTORING SYSTEM - ai_exam_evaluation
color 0A

echo ============================================================
echo    AI EXAM EVALUATION - PROCTORING SYSTEM
echo ============================================================
echo.

cd /d C:\EYE

:: Check if virtual environment exists
if not exist "venv\Scripts\activate" (
    echo [ERROR] Virtual environment not found!
    echo Please run: python -m venv venv
    pause
    exit /b
)

:: Activate Python environment
echo [1/4] Activating Python environment...
call venv\Scripts\activate

:: Check if Flask is installed
pip show flask > nul 2>&1
if errorlevel 1 (
    echo [INFO] Installing Flask...
    pip install flask flask-cors
)

:: Start Flask Server
echo [2/4] Starting Flask server...
start "Flask Server" cmd /k "cd /d C:\EYE && venv\Scripts\activate && python flask_server.py"

:: Wait for Flask to initialize
timeout /t 3 /nobreak > nul

:: Start Python Proctoring System
echo [3/4] Starting Proctoring System...
start "Proctoring System" cmd /k "cd /d C:\EYE && venv\Scripts\activate && python main.py"

:: Wait a bit
timeout /t 2 /nobreak > nul

:: Start Flutter App
echo [4/4] Starting AI Exam Evaluation App...
cd flutter_app
if exist "ai_exam_evaluation.exe" (
    start "" "ai_exam_evaluation.exe"
    echo [OK] App started successfully!
) else (
    echo [ERROR] ai_exam_evaluation.exe not found in flutter_app folder!
    echo Please place your EXE file in: C:\EYE\flutter_app\
)

cd ..

echo.
echo ============================================================
echo   ALL SYSTEMS RUNNING!
echo ============================================================
echo   Flask Server:     http://localhost:5000
echo   Proctoring:       Active (camera monitoring)
echo   AI Exam App:      Running
echo ============================================================
echo.
echo   To stop all services, close this window or press Ctrl+C
echo.

:: Keep window open and wait for user input
pause > nul

:: Cleanup on exit
echo.
echo Shutting down all services...
taskkill /F /IM python.exe > nul 2>&1
taskkill /F /IM ai_exam_evaluation.exe > nul 2>&1
echo Done.