@echo off
setlocal
cd /d "%~dp0"
docker compose up -d --build api
if errorlevel 1 goto :failed
echo DND-BofA Rules API rebuilt and restarted.
exit /b 0
:failed
echo API restart failed. Check: docker compose logs api
exit /b 1
