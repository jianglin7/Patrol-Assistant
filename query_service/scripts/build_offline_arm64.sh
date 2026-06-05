#!/usr/bin/env bash
set -euo pipefail

# Build and export linux/arm64 image for offline delivery.
IMAGE_NAME="${IMAGE_NAME:-patrol-assistant}"
IMAGE_TAG="${IMAGE_TAG:-v6}"
OUTPUT_TAR="${OUTPUT_TAR:-${IMAGE_NAME}-${IMAGE_TAG}-arm64.tar}"
BASE_IMAGE="${BASE_IMAGE:-python:3.10-slim}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

echo "[1/3] Building ${IMAGE_NAME}:${IMAGE_TAG} (linux/arm64)..."
echo "       base image: ${BASE_IMAGE}"
docker build \
  --platform linux/arm64 \
  --build-arg BASE_IMAGE="${BASE_IMAGE}" \
  -t "${IMAGE_NAME}:${IMAGE_TAG}" \
  "${PROJECT_DIR}"

echo "[2/3] Exporting image to ${OUTPUT_TAR}..."
docker save -o "${PROJECT_DIR}/${OUTPUT_TAR}" "${IMAGE_NAME}:${IMAGE_TAG}"

echo "[3/3] Done."
echo "Image tar: ${PROJECT_DIR}/${OUTPUT_TAR}"
echo "Target host import command:"
echo "  docker load -i ${OUTPUT_TAR}"
