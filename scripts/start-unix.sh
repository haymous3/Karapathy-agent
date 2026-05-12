#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

IMAGE_NAME="pm-mvp-app:latest"
CONTAINER_NAME="pm-mvp-app"
PORT="${PM_MVP_PORT:-8000}"

if ! docker info >/dev/null 2>&1; then
  echo "Docker daemon is not reachable. Start Docker Desktop/Docker Engine, then rerun this script."
  exit 1
fi

echo "Building Docker image: ${IMAGE_NAME}"
docker build -t "${IMAGE_NAME}" .

EXISTING_ID="$(docker ps -aq --filter "name=^${CONTAINER_NAME}$")"
if [[ -n "${EXISTING_ID}" ]]; then
  echo "Removing existing container: ${CONTAINER_NAME}"
  docker rm -f "${CONTAINER_NAME}" >/dev/null
fi

echo "Starting container: ${CONTAINER_NAME} on port ${PORT}"
docker run -d --name "${CONTAINER_NAME}" -p "${PORT}:8000" --env-file ".env" "${IMAGE_NAME}" >/dev/null

echo "Waiting for service warm-up..."
for _ in $(seq 1 20); do
  if curl --silent --show-error "http://127.0.0.1:${PORT}/health" >/dev/null; then
    break
  fi
  sleep 1
done

echo "Health response:"
curl --silent --show-error "http://127.0.0.1:${PORT}/health"
echo
echo "App available at http://127.0.0.1:${PORT}/"
