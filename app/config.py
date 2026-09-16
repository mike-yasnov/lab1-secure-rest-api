import os
import secrets


class Settings:
    """Настройки, загружаемые из окружения (см. .env.example)."""

    SECRET_KEY: str = os.environ.get("SECRET_KEY") or secrets.token_urlsafe(32)

    JWT_ALGORITHM: str = "HS256"

    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(
        os.environ.get("ACCESS_TOKEN_EXPIRE_MINUTES", "30")
    )

    DATABASE_URL: str = os.environ.get("DATABASE_URL", "sqlite:///./app.db")


settings = Settings()
