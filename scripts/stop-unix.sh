#!/usr/bin/env bash
set -euo pipefail

CONTAINER_NAME="pm-mvp-app"

EXISTING_ID="$(docker ps -aq --filter "name=^${CONTAINER_NAME}$")"
if [[ -n "${EXISTING_ID}" ]]; then
  echo "Stopping and removing container: ${CONTAINER_NAME}"
  docker rm -f "${CONTAINER_NAME}" >/dev/null
  echo "Container removed."
else
  echo "Container not found: ${CONTAINER_NAME}"
fi
