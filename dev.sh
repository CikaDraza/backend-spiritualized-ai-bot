#!/usr/bin/env bash
# Start the Spiritualized backend in dev mode:
#   1) bring up the local Docker Postgres (host port 5455)
#   2) point the app at it via POSTGRES_DSN (the .env DATABASE_URL is Railway-internal only)
#   3) run Alembic migrations
#   4) run uvicorn with --reload
#
# Usage:  ./dev.sh            # full flow
#         PORT=8001 ./dev.sh  # custom port
#         SKIP_DB=1 ./dev.sh  # don't touch Docker (DB already running)
#         SKIP_MIGRATE=1 ./dev.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

VENV="$SCRIPT_DIR/../.venv"
PORT="${PORT:-8000}"
# Local Docker Postgres (docker-compose.yml): spirit/spirit @ localhost:5455/spiritualized.
export POSTGRES_DSN="${POSTGRES_DSN:-postgresql+asyncpg://spirit:spirit@localhost:5455/spiritualized}"
# The .env URLs point at prod (Railway/Vercel). Override locally so the verification link points to
# the local frontend, whose BFF verifies against THIS backend — token and check stay on one system.
export FRONTEND_URL="${FRONTEND_URL:-http://localhost:3016}"
export BACKEND_URL="${BACKEND_URL:-http://localhost:${PORT}}"

# --- venv -----------------------------------------------------------------------
if [[ ! -x "$VENV/bin/python" ]]; then
  echo "✗ venv not found at $VENV — create it: python3 -m venv ../.venv && ../.venv/bin/pip install -r requirements.txt" >&2
  exit 1
fi
# shellcheck disable=SC1091
source "$VENV/bin/activate"

# --- docker compose (v2 'docker compose' or legacy 'docker-compose') -------------
compose() {
  if docker compose version >/dev/null 2>&1; then docker compose "$@"
  else docker-compose "$@"; fi
}

# --- 1) Postgres ----------------------------------------------------------------
if [[ "${SKIP_DB:-0}" != "1" ]]; then
  echo "▶ Starting Postgres (docker)…"
  compose up -d postgres
  echo "▶ Waiting for Postgres to accept connections…"
  for _ in $(seq 1 30); do
    if compose exec -T postgres pg_isready -U spirit -d spiritualized >/dev/null 2>&1; then
      echo "✓ Postgres ready"
      break
    fi
    sleep 1
  done
fi

# --- 2) migrations --------------------------------------------------------------
if [[ "${SKIP_MIGRATE:-0}" != "1" ]]; then
  echo "▶ alembic upgrade head"
  alembic upgrade head
fi

# --- 3) run ---------------------------------------------------------------------
echo "▶ uvicorn on http://localhost:${PORT}  (reload)  · DSN=${POSTGRES_DSN}"
exec uvicorn app.main:app --reload --port "$PORT"
