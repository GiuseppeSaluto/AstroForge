@echo off
cd /d "%~dp0"

echo ===================================
echo   AstroForge - avvio in corso...
echo ===================================
echo.

where docker >nul 2>nul
if errorlevel 1 (
    echo Docker non e' installato su questo computer.
    echo Scaricalo da: https://www.docker.com/products/docker-desktop/
    pause
    exit /b 1
)

echo Scarico e avvio i servizi ^(puo' richiedere qualche minuto al primo avvio^)...
docker compose up -d --wait mongodb rust-engine python-api

echo.
echo Servizi pronti. Apro la dashboard...
echo ^(premi 'q' nella dashboard per uscire^)
echo.

docker compose run --rm dashboard

echo.
echo Chiusura dei servizi in corso...
docker compose down

pause
