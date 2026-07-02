#!/usr/bin/env bash
# Builda e pubblica su Docker Hub le immagini custom del progetto
# (rust-engine, python-api, dashboard).
#
# Solo linux/amd64: il build multi-arch (arm64) richiederebbe emulatori QEMU
# registrati con privilegi root reali sul kernel host, incompatibili con
# l'installazione Docker rootless usata qui. Su Mac Apple Silicon, Docker
# Desktop esegue comunque immagini amd64 via emulazione interna.
#
# Prerequisiti: `docker login` gia' eseguito con l'account che pubblica.
#
# Uso:
#   ./publish_images.sh [tag]
#   ./publish_images.sh          # pubblica come "latest"
#   ./publish_images.sh v1.0.0   # pubblica anche con un tag versionato

set -euo pipefail

DOCKERHUB_USER="giuseppesaluto"
TAG="${1:-latest}"
ROOT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"

echo "Pubblico le immagini come ${DOCKERHUB_USER}/astroforge-*:${TAG} (linux/amd64)"

docker buildx build --platform linux/amd64 \
    -t "${DOCKERHUB_USER}/astroforge-rust-engine:${TAG}" \
    --push "${ROOT_DIR}/services/rust-engine"

docker buildx build --platform linux/amd64 \
    -t "${DOCKERHUB_USER}/astroforge-python-api:${TAG}" \
    --push "${ROOT_DIR}/services/python-api"

docker buildx build --platform linux/amd64 \
    -t "${DOCKERHUB_USER}/astroforge-dashboard:${TAG}" \
    --push "${ROOT_DIR}/services/dashboard"

echo "Fatto."
