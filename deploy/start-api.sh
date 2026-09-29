#!/bin/sh
# Start the API: bring the database up to date, add the demo officials, then serve.
# Hosts set PORT (Render uses 10000); locally it defaults to 8000.
set -e
alembic upgrade head
python -m app.seed
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}" \
  --proxy-headers --forwarded-allow-ips '*'
