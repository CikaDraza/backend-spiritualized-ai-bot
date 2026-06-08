from __future__ import annotations

from typing import Literal, Optional, cast
from urllib.parse import quote_plus, urlsplit, urlunsplit

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def normalize_mongodb_uri(uri: str) -> str:
    parsed = urlsplit(uri)
    if not parsed.scheme or "mongodb" not in parsed.scheme:
        return uri

    if "@" not in parsed.netloc:
        return uri

    userinfo, hostinfo = parsed.netloc.rsplit("@", 1)
    if ":" not in userinfo:
        return uri

    user, password = userinfo.split(":", 1)
    quoted_user = quote_plus(user)
    quoted_password = quote_plus(password)
    safe_netloc = f"{quoted_user}:{quoted_password}@{hostinfo}"
    return urlunsplit((parsed.scheme, safe_netloc, parsed.path, parsed.query, parsed.fragment))


def to_asyncpg_dsn(url: str) -> str:
    """Normalize a Postgres URL to the asyncpg driver form SQLAlchemy expects."""
    if url.startswith("postgresql+asyncpg://"):
        return url
    if url.startswith("postgresql://"):
        return "postgresql+asyncpg://" + url[len("postgresql://") :]
    if url.startswith("postgres://"):
        return "postgresql+asyncpg://" + url[len("postgres://") :]
    return url


class Settings(BaseSettings):
    # extra="ignore" so unrelated .env keys (APP_NAME, FRONTEND_URL, UPSTASH_*, RESEND_*, ...)
    # don't raise during config load — they belong to other layers / future PRs.
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    OPENAI_API_KEY: str = ""
    SECRET_KEY: str = "changeme"

    # Auth token lifetimes. Access is short-lived (JWT); refresh is long-lived (opaque, in DB).
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    EMAIL_VERIFICATION_EXPIRE_HOURS: int = 24

    # CORS / cookies. In prod (cross-site Vercel<->Railway) set COOKIE_SECURE=true and
    # COOKIE_SAMESITE=none; locally (same-site localhost) the lax/insecure defaults work.
    FRONTEND_URL: str = "http://localhost:3016"
    BACKEND_URL: str = "http://localhost:8000"
    COOKIE_SECURE: bool = False
    COOKIE_SAMESITE: Literal["lax", "strict", "none"] = "lax"
    COOKIE_DOMAIN: Optional[str] = None

    # Email (Resend). When unset/placeholder, email.py logs the verification link instead of
    # sending (dev-fallback until the custom domain + DNS are ready).
    RESEND_API_KEY: str = ""
    EMAIL_FROM: str = "Spiritualized <onboarding@resend.dev>"

    # Seed admin (used by `python -m app.seed_admin`). Avoid special-use TLDs (.local/.test) —
    # email-validator rejects them.
    ADMIN_EMAIL: str = "admin@spiritualized.app"
    ADMIN_PASSWORD: str = "change-me-admin"
    SEED_ADMIN_NAME: str = "Admin"

    # Rate limiting (Upstash Redis REST). If creds are unset the limiter no-ops (fails open).
    UPSTASH_REDIS_REST_URL: str = ""
    UPSTASH_REDIS_REST_TOKEN: str = ""
    RATE_LIMIT_ENABLED: bool = True
    CHAT_RATE_LIMIT: int = 20
    RATE_LIMIT_WINDOW_SECONDS: int = 60

    POSTGRES_DSN: str = "postgresql+asyncpg://user:pass@localhost:5432/spiritualized"
    DATABASE_URL: str = ""
    RAILWAY_DATABASE_URL: str = ""
    MONGODB_URI: str = "mongodb://localhost:27017/spiritualized"
    MONGODB_URL: str = ""
    RAILWAY_MONGODB_URI: str = ""
    MONGODB_DB: str = "spiritualized"
    BACKEND_PORT: int = 8000
    PORT: Optional[int] = None

    @model_validator(mode="before")
    @classmethod
    def resolve_railway_settings(cls, values: object) -> object:
        if not isinstance(values, dict):
            return values
        data = cast(dict[str, object], values)

        # Railway / Neon provide DATABASE_URL; derive the asyncpg DSN when POSTGRES_DSN is unset.
        postgres = str(data.get("POSTGRES_DSN") or "")
        database_url = str(data.get("DATABASE_URL") or data.get("RAILWAY_DATABASE_URL") or "")
        if not postgres and database_url:
            data["POSTGRES_DSN"] = to_asyncpg_dsn(database_url)
        elif postgres:
            data["POSTGRES_DSN"] = to_asyncpg_dsn(postgres)

        mongodb = str(data.get("MONGODB_URI") or "")
        mongodb_url = str(data.get("MONGODB_URL") or data.get("RAILWAY_MONGODB_URI") or "")
        if not mongodb and mongodb_url:
            data["MONGODB_URI"] = mongodb_url

        mongodb_uri = data.get("MONGODB_URI")
        if mongodb_uri:
            data["MONGODB_URI"] = normalize_mongodb_uri(str(mongodb_uri))

        port = data.get("PORT")
        if port:
            data["BACKEND_PORT"] = int(str(port))

        return data


settings = Settings()
