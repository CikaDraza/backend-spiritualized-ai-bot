from typing import Any, Dict, Optional
from urllib.parse import quote_plus, urlsplit, urlunsplit

from pydantic import BaseSettings, root_validator


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


class Settings(BaseSettings):
    OPENAI_API_KEY: str = ""
    SECRET_KEY: str = "changeme"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    POSTGRES_DSN: str = "postgresql+asyncpg://user:pass@localhost:5432/spiritualized"
    DATABASE_URL: str = ""
    RAILWAY_DATABASE_URL: str = ""
    MONGODB_URI: str = "mongodb://localhost:27017/spiritualized"
    MONGODB_URL: str = ""
    RAILWAY_MONGODB_URI: str = ""
    MONGODB_DB: str = "spiritualized"
    BACKEND_PORT: int = 8000
    PORT: Optional[int] = None

    @root_validator(pre=True)
    def resolve_railway_settings(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        postgres = values.get("POSTGRES_DSN") or ""
        database_url = values.get("DATABASE_URL") or values.get("RAILWAY_DATABASE_URL") or ""
        if not postgres and database_url:
            if database_url.startswith("postgres://"):
                database_url = database_url.replace("postgres://", "postgresql+asyncpg://", 1)
            values["POSTGRES_DSN"] = database_url

        mongodb = values.get("MONGODB_URI") or ""
        mongodb_url = values.get("MONGODB_URL") or values.get("RAILWAY_MONGODB_URI") or ""
        if not mongodb and mongodb_url:
            values["MONGODB_URI"] = mongodb_url

        if values.get("MONGODB_URI"):
            values["MONGODB_URI"] = normalize_mongodb_uri(values["MONGODB_URI"])

        port = values.get("PORT")
        if port:
            values["BACKEND_PORT"] = int(port)

        return values

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
