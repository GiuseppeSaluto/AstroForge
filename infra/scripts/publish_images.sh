#!/usr/bin/env bash
# Builds and publishes the project's custom images to Docker Hub
# (rust-engine, python-api, dashboard).
#
# linux/amd64 only: multi-arch (arm64) builds would require QEMU emulators
# registered with real root privileges on the host kernel, which is
# incompatible with the rootless Docker setup used here. On Apple Silicon
# Macs, Docker Desktop still runs amd64 images fine via internal emulation.
#
# Prerequisites: `docker login` already done with the publishing account.
#
# Usage:
#   ./publish_images.sh [tag]
#   ./publish_images.sh          # publishes as "latest"
#   ./publish_images.sh v1.0.0   # also publishes with a versioned tag

set -euo pipefail

DOCKERHUB_USER="giuseppesaluto"
TAG="${1:-latest}"
ROOT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"

echo "Publishing images as ${DOCKERHUB_USER}/astroforge-*:${TAG} (linux/amd64)"

docker buildx build --platform linux/amd64 \
    -t "${DOCKERHUB_USER}/astroforge-rust-engine:${TAG}" \
    --push "${ROOT_DIR}/services/rust-engine"

docker buildx build --platform linux/amd64 \
    -t "${DOCKERHUB_USER}/astroforge-python-api:${TAG}" \
    --push "${ROOT_DIR}/services/python-api"

docker buildx build --platform linux/amd64 \
    -t "${DOCKERHUB_USER}/astroforge-dashboard:${TAG}" \
    --push "${ROOT_DIR}/services/dashboard"

echo "Done."
