#!/bin/sh
# Apply migrations, seed (idempotent, controlled by SEED_* env vars), then start the API.
set -e
echo "Running database migrations..."
alembic upgrade head
echo "Seeding (SEED_EMISSION_FACTORS=${SEED_EMISSION_FACTORS:-true}, SEED_DEMO_DATA=${SEED_DEMO_DATA:-false})..."
python -m app.seed
echo "Starting API on port ${PORT:-8000}"
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}" --proxy-headers --forwarded-allow-ips="*" --workers "${WEB_CONCURRENCY:-1}"
