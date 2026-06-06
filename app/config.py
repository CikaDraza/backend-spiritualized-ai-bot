from pydantic import BaseSettings


class Settings(BaseSettings):
    OPENAI_API_KEY: str = ""
    SECRET_KEY: str = "changeme"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    POSTGRES_DSN: str = "postgresql+asyncpg://user:pass@localhost:5432/spiritualized"
    MONGODB_URI: str = "mongodb://localhost:27017/spiritualized"
    MONGODB_DB: str = "spiritualized"
    BACKEND_PORT: int = 8000

    class Config:
        env_file = ".env"


settings = Settings()
