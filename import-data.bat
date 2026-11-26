@echo off
setlocal
cd /d "%~dp0"
docker compose --profile tools run --rm seed
if errorlevel 1 goto :failed
echo SRD data imported. This command can be rerun safely after catalog updates.
exit /b 0
:failed
echo Import failed. Check: docker compose --profile tools logs seed
exit /b 1
