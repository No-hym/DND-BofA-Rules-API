@echo off
setlocal
cd /d "%~dp0"
docker compose down
if errorlevel 1 exit /b 1
echo DND-BofA Rules API stopped. Database volume was preserved.
