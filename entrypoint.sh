#!/bin/sh
set -e

echo "=== TrafficVision AI Backend Startup ==="
echo "Running database migrations (Alembic)..."

# Run Alembic migrations to current head
if ! alembic upgrade head; then
    echo "ERROR: Database migration failed. Aborting application startup." >&2
    exit 1
fi

echo "Migrations completed successfully. Starting application server..."

# Start Uvicorn with standard production parameters
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}" --workers "${WEB_CONCURRENCY:-2}"
