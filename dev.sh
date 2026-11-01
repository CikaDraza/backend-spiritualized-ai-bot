#!/usr/bin/env bash
# Start the Spiritualized backend in dev mode — safely, by default:
#   1) bring up the local Docker Postgres (host port 5455)
#   2) make sure the chosen local database exists (created if missing — never dropped or reset)
#   3) point the app at it via POSTGRES_DSN (the .env DATABASE_URL is Railway-internal only)
#   4) switch OFF every paid / production service from .env (OpenAI, Resend, Upstash)
#   5) run Alembic migrations
#   6) run uvicorn with --reload
#
# Usage:  ./dev.sh                                  # full flow, external services off
#         DB_NAME=spiritualized_walkthrough ./dev.sh  # a separate, empty local database
#         PORT=8001 ./dev.sh                        # custom port
#         SKIP_DB=1 ./dev.sh                        # don't touch Docker (DB already running)
#         SKIP_MIGRATE=1 ./dev.sh
#         USE_REAL_SERVICES=1 ./dev.sh              # deliberately use the OpenAI/Resend/Upstash keys from .env
#         VENV=/path/to/venv ./dev.sh               # another virtualenv (default: ../.venv)
#
# Why services are off by default: .env may hold production keys. Without this, a local
# registration sends a real email from the production domain and every tutor turn spends
# OpenAI credit. With them off, the verification link is written to this log
# ("EMAIL DEV-FALLBACK") and the tutor answers in dev mode.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

VENV="${VENV:-$SCRIPT_DIR/../.venv}"
PORT="${PORT:-8000}"
DB_NAME="${DB_NAME:-spiritualized}"
if [[ ! "$DB_NAME" =~ ^[a-z_][a-z0-9_]*$ ]]; then
  echo "✗ DB_NAME must be lowercase letters, digits and underscores: $DB_NAME" >&2
  exit 1
fi
# Local Docker Postgres (docker-compose.yml): spirit/spirit @ localhost:5455/<DB_NAME>.
export POSTGRES_DSN="${POSTGRES_DSN:-postgresql+asyncpg://spirit:spirit@localhost:5455/${DB_NAME}}"
case "$POSTGRES_DSN" in
  *@localhost:*|*@127.0.0.1:*) ;;
  *)
    if [[ "${ALLOW_REMOTE_DB:-0}" != "1" ]]; then
      echo "✗ POSTGRES_DSN does not point at a local database. Set ALLOW_REMOTE_DB=1 if that is really intended." >&2
      exit 1
    fi
    ;;
esac
# The .env URLs point at prod (Railway/Vercel). Override locally so the verification link points to
# the local frontend, whose BFF verifies against THIS backend — token and check stay on one system.
export FRONTEND_URL="${FRONTEND_URL:-http://localhost:3016}"
export BACKEND_URL="${BACKEND_URL:-http://localhost:${PORT}}"

# --- external services ----------------------------------------------------------
# Environment variables win over .env (pydantic-settings), so empty values switch them off.
if [[ "${USE_REAL_SERVICES:-0}" == "1" ]]; then
  SERVICES="ON — real OpenAI / Resend / Upstash from .env (costs money, sends real email)"
else
  export OPENAI_API_KEY="" RESEND_API_KEY="" UPSTASH_REDIS_REST_URL="" UPSTASH_REDIS_REST_TOKEN=""
  SERVICES="off — verification links in this log, tutor in dev mode, no rate-limit store"
fi

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
  # --- 2) the chosen database: created when missing, never dropped -------------
  if [[ -z "$(compose exec -T postgres psql -U spirit -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname = '${DB_NAME}'")" ]]; then
    echo "▶ Creating the empty local database ${DB_NAME}"
    compose exec -T postgres psql -U spirit -d postgres -c "CREATE DATABASE ${DB_NAME}" >/dev/null
  fi
fi

# --- 3) migrations --------------------------------------------------------------
if [[ "${SKIP_MIGRATE:-0}" != "1" ]]; then
  echo "▶ alembic upgrade head (${DB_NAME})"
  alembic upgrade head
fi

# --- 4) run ---------------------------------------------------------------------
echo "▶ uvicorn on http://localhost:${PORT}  (reload)"
echo "  database: ${DB_NAME} (local)"
echo "  external services: ${SERVICES}"
exec uvicorn app.main:app --reload --port "$PORT"
