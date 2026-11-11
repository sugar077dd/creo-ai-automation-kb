@echo off
rem Right-click -> Run as administrator
setlocal
set "PLAN=%~1"
if "%PLAN%"=="" set "PLAN=D:\deepseek\CreoAuto\plans\plate_890.json"
if not exist "%PLAN%" ( echo [ERROR] plan not found: %PLAN% & pause & exit /b 1 )
"D:\deepseek\mechdog_extract\MCP_CREO_MechDog-main\.venv\Scripts\python.exe" -u "D:\deepseek\CreoAuto\run_plan.py" "%PLAN%"
echo.
echo [log] D:\deepseek\CreoAuto\logs\plan_run.log
pause