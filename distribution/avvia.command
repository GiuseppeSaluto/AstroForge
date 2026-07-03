#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"

echo "==================================="
echo "  AstroForge - starting up..."
echo "==================================="
echo

if ! command -v docker >/dev/null 2>&1; then
    echo "Docker is not installed on this computer."
    echo "Download it from: https://www.docker.com/products/docker-desktop/"
    read -rp "Press Enter to close..."
    exit 1
fi

echo "Downloading and starting services (may take a few minutes on first run)..."
docker compose up -d --wait mongodb rust-engine python-api

echo
echo "Services ready. Opening the dashboard..."
echo "(press 'q' in the dashboard to quit)"
echo

docker compose run --rm dashboard

echo
echo "Shutting down services..."
docker compose down

read -rp "Done. Press Enter to close this window..."
