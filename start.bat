@echo off
setlocal
cd /d "%~dp0"
docker compose up -d --build
if errorlevel 1 goto :failed
echo DND-BofA Rules API is starting at http://localhost:8080
exit /b 0
:failed
echo Failed to start the API. Check Docker Desktop and run: docker compose logs
exit /b 1
