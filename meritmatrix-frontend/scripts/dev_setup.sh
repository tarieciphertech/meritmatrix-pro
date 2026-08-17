#!/usr/bin/env bash
# Convenience script: bootstrap local development environment.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [ ! -f .env ]; then
  echo "Creating .env from .env.example ..."
  cp .env.example .env
  echo "IMPORTANT: edit .env and set SECRET_KEY / JWT_SECRET before continuing."
fi

echo "Starting PostgreSQL + backend via Docker Compose ..."
docker compose up --build -d db backend

echo "Waiting for the API to become healthy ..."
for _ in $(seq 1 30); do
  if curl -sf http://localhost:8000/health > /dev/null; then
    echo "Backend is healthy: http://localhost:8000/health"
    exit 0
  fi
  sleep 1
done

echo "Backend did not become healthy in time. Check: docker compose logs backend" >&2
exit 1
