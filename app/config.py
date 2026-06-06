from typing import Any, Dict, Optional

from pydantic import BaseSettings, root_validator


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

        port = values.get("PORT")
        if port:
            values["BACKEND_PORT"] = int(port)

        return values

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
