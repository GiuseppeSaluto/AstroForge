#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"

echo "==================================="
echo "  AstroForge - avvio in corso..."
echo "==================================="
echo

if ! command -v docker >/dev/null 2>&1; then
    echo "Docker non e' installato su questo computer."
    echo "Scaricalo da: https://www.docker.com/products/docker-desktop/"
    read -rp "Premi Invio per chiudere..."
    exit 1
fi

echo "Scarico e avvio i servizi (puo' richiedere qualche minuto al primo avvio)..."
docker compose up -d --wait mongodb rust-engine python-api

echo
echo "Servizi pronti. Apro la dashboard..."
echo "(premi 'q' nella dashboard per uscire)"
echo

docker compose run --rm dashboard

echo
echo "Chiusura dei servizi in corso..."
docker compose down

read -rp "Fatto. Premi Invio per chiudere questa finestra..."
