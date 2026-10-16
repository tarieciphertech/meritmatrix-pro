#!/usr/bin/env bash
set -Eeuo pipefail

cd "$(dirname "$0")"
COMPOSE=(docker compose --file docker-compose.production.yml)

if [[ ! -f .env ]]; then
  echo "Missing meritmatrix-backend/.env. Create it from .env.example and configure production values." >&2
  exit 1
fi

if ! grep -Eq '^ENVIRONMENT=production$' .env; then
  echo "Refusing deployment: .env must contain ENVIRONMENT=production." >&2
  exit 1
fi
if ! grep -Eq '^DATABASE_URL=postgresql(\+psycopg)?://' .env; then
  echo "Refusing deployment: DATABASE_URL must point to PostgreSQL." >&2
  exit 1
fi
if ! grep -Eq '^SECRET_KEY=.{32,}$' .env || ! grep -Eq '^JWT_SECRET=.{32,}$' .env; then
  echo "Refusing deployment: set independent strong SECRET_KEY and JWT_SECRET values (at least 32 characters each)." >&2
  exit 1
fi

secret_key="$(sed -n 's/^SECRET_KEY=//p' .env | tail -n 1)"
jwt_secret="$(sed -n 's/^JWT_SECRET=//p' .env | tail -n 1)"
if [[ -z "$secret_key" || -z "$jwt_secret" || "$secret_key" == "$jwt_secret" ]]; then
  echo "Refusing deployment: SECRET_KEY and JWT_SECRET must be distinct non-empty values." >&2
  exit 1
fi
if grep -Eq '^CORS_ORIGINS=.*(localhost|127\.0\.0\.1)' .env; then
  echo "Refusing deployment: replace local development origins in CORS_ORIGINS." >&2
  exit 1
fi
if grep -Eq '^SMS_PROVIDER=mock$|^OTP_MOCK_STATIC_CODE=.+$' .env; then
  echo "Refusing deployment: configure a real SMS/OTP provider and remove the mock OTP code." >&2
  exit 1
fi

if [[ "${DB_BACKUP_CONFIRMED:-}" != "1" ]]; then
  echo "Before deploying, take and verify a PostgreSQL backup, then rerun with DB_BACKUP_CONFIRMED=1." >&2
  exit 1
fi

echo "Validating production Compose configuration…"
"${COMPOSE[@]}" config --quiet

echo "Building production API image…"
"${COMPOSE[@]}" build backend

echo "Applying database migrations…"
"${COMPOSE[@]}" run --rm backend alembic upgrade head

echo "Starting production API…"
"${COMPOSE[@]}" up -d --remove-orphans backend

echo "Waiting for API health check…"
for attempt in $(seq 1 20); do
  if curl --fail --silent --show-error http://127.0.0.1:8000/health; then
    echo
    echo "MeritMatrix API is healthy locally. Verify the public HTTPS hostname and login flow through the reverse proxy."
    exit 0
  fi
  sleep 3
done

echo "API health check failed. Inspect: docker compose -f docker-compose.production.yml logs --tail=150 backend" >&2
exit 1
