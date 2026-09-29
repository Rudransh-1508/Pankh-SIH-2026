#!/bin/sh
# Start the simulators. Hosts set PORT (Render uses 10000); locally it defaults to 8100.
set -e
exec uvicorn pankh_simulators.app:app --host 0.0.0.0 --port "${PORT:-8100}"
