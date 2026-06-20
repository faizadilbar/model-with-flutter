@echo off
cd /d C:\EYE\flutter_app

echo Starting app with logging...
echo ======================================== > app_log.txt
echo App launched at %date% %time% >> app_log.txt
echo ======================================== >> app_log.txt

:: Run and capture output
ai_exam_evaluation.exe >> app_log.txt 2>&1

echo App exited. Check app_log.txt for errors
type app_log.txt
pause