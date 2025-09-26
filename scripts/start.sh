#!/bin/bash
#
# Start InsightHub using the local virtual environment.
# This is intended for local dev or production with systemd.
#
# Make sure your `.env` is in the project root.
# Requires Python 3 and `uvicorn` installed via `.venv`.

# Get directory where script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Activate virtualenv
source "$PROJECT_ROOT/.venv/bin/activate"

# Optional: export environment variables from .env
if [ -f "$PROJECT_ROOT/.env" ]; then
  export $(grep -v '^#' "$PROJECT_ROOT/.env" | xargs)
fi

# Run the FastAPI app
exec uvicorn app.main:main_app \
  --host 0.0.0.0 \
  --port 8000
