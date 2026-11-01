# Spiritualized Language Tutor — backend

FastAPI backend of the Spiritualized Language Tutor: accounts, Learning Spaces, the AI tutor conversation and learning progress. PostgreSQL holds all data (SQLAlchemy async + Alembic migrations); OpenAI writes the tutor's turns; Resend sends email; Upstash Redis keeps rate limits.

The frontend is [`CikaDraza/spiritualized-ai-bot`](https://github.com/CikaDraza/spiritualized-ai-bot) (Next.js). Its server-side routes call this API.

## Run locally — safely

Requirements: Python 3.10+, Docker.

```bash
python3 -m venv ../.venv && ../.venv/bin/pip install -r requirements.txt   # once
cp .env.example .env                                                       # once; see below
./dev.sh
```

`dev.sh` does the following:
- starts Postgres in Docker on port 5455;
- creates the chosen local database if it does not exist (it never drops or resets one);
- runs `alembic upgrade head`;
- starts uvicorn on <http://localhost:8000> with reload.

**External services are off by default.** `dev.sh` empties the OpenAI, Resend and Upstash variables for the run, whatever `.env` holds, so a local run never sends real email or spends money:
- **email:** the verification link is written to the backend log as `EMAIL DEV-FALLBACK`; open it in the browser;
- **tutor:** it answers with a fixed dev-mode reply;
- **rate limits:** off.

`USE_REAL_SERVICES=1 ./dev.sh` uses the keys from `.env` on purpose. It costs money and sends real email.

`dev.sh` also points the backend at local URLs (`FRONTEND_URL=http://localhost:3016`) and refuses a database that is not local unless `ALLOW_REMOTE_DB=1`.

| Option | Effect |
|---|---|
| `DB_NAME=spiritualized_walkthrough ./dev.sh` | a separate, empty local database (created and migrated); the default is `spiritualized` |
| `PORT=8001 ./dev.sh` | another port |
| `SKIP_DB=1` / `SKIP_MIGRATE=1` | do not touch Docker / do not migrate |
| `VENV=/path/to/venv` | another virtualenv (default `../.venv`) |

Do **not** start the backend with a bare `uvicorn app.main:app` when `.env` holds production keys. That path uses them.

An admin account for local use: `python -m app.seed_admin` (from `ADMIN_EMAIL` / `ADMIN_PASSWORD`).

API documentation while running: <http://localhost:8000/docs>.

## API

| Area | Routes |
|---|---|
| Health | `GET /` |
| Accounts | `POST /auth/register`, `/auth/login`, `/auth/refresh`, `/auth/logout`; `GET /auth/me`, `/auth/verify`; `POST /auth/resend-verification` |
| Learning Spaces (verified email) | `GET`/`POST /spaces`, `GET`/`DELETE /spaces/{id}` — at most 5 active per learner |
| Saved tests (verified email) | `GET`/`POST /tests`, `DELETE /tests/{id}` — at most 5 |
| Tutor | `GET /tutor/personas`; `POST /tutor/turn`, `/tutor/session/complete` (verified email); `GET /tutor/progress` |
| Legacy chat | `POST /chat` — the original single-call chat; open without a login, not used by the current frontend |

Sessions use httpOnly cookies: a short-lived JWT access cookie and a rotating refresh cookie scoped to `/auth`.

## Production

Railway deploys `main` (`Procfile`: `alembic upgrade head`, then uvicorn). Railway injects `DATABASE_URL`, which wins over `POSTGRES_DSN` there. Pushing a feature branch does not deploy.
