@echo off
echo ========================================
echo   FORCING APP WINDOW TO SHOW
echo ========================================
echo.

cd /d C:\EYE\flutter_app

:: Kill any existing instance
taskkill /F /IM ai_exam_evaluation.exe > nul 2>&1

:: Run with high priority
start /MAX ai_exam_evaluation.exe

echo App started in maximized mode!
echo If still no window, press Alt+Tab to find it
pause