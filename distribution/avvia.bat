@echo off
cd /d "%~dp0"

echo ===================================
echo   AstroForge - starting up...
echo ===================================
echo.

where docker >nul 2>nul
if errorlevel 1 (
    echo Docker is not installed on this computer.
    echo Download it from: https://www.docker.com/products/docker-desktop/
    pause
    exit /b 1
)

echo Downloading and starting services ^(may take a few minutes on first run^)...
docker compose up -d --wait mongodb rust-engine python-api

echo.
echo Services ready. Opening the dashboard...
echo ^(press 'q' in the dashboard to quit^)
echo.

docker compose run --rm dashboard

echo.
echo Shutting down services...
docker compose down

pause
