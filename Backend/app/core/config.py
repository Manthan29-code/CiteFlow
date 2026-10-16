from pathlib import Path
from typing import Optional
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Resolve paths to root repository for global .env file
CURRENT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = CURRENT_DIR.parent.parent
ROOT_DIR = BACKEND_DIR.parent
ROOT_ENV = ROOT_DIR / ".env"
BACKEND_ENV = BACKEND_DIR / ".env"


class Settings(BaseSettings):
    # App
    APP_ENV: str = Field(default="development", description="development | production")
    APP_HOST: str = Field(default="0.0.0.0")
    APP_PORT: int = Field(default=8000)
    LOG_LEVEL: str = Field(default="INFO")
    CORS_ALLOW_ORIGINS: str = Field(default="http://localhost:5173")
    FORWARDED_ALLOW_IPS: str = Field(default="127.0.0.1")
    TEMP_DIR: str = Field(default="./tmp")

    # Database
    DATABASE_URL: str = Field(
        default="postgresql+psycopg://citegen:citegen@localhost:5432/citegen"
    )
    DB_POOL_SIZE: int = Field(default=5)

    @property
    def async_database_url(self) -> str:
        """Ensures the URL uses postgresql+psycopg:// driver for async SQLAlchemy."""
        url = self.DATABASE_URL.strip()
        if url.startswith("postgres://"):
            return "postgresql+psycopg://" + url[len("postgres://"):]
        if url.startswith("postgresql://") and not url.startswith("postgresql+"):
            return "postgresql+psycopg://" + url[len("postgresql://"):]
        return url

    # Auth
    JWT_SECRET: str = Field(
        default="citeflow-dev-secret-key-at-least-32-chars-long",
        description="Must be at least 32 characters in production",
    )
    JWT_ALGORITHM: str = Field(default="HS256")
    ACCESS_TOKEN_MINUTES: int = Field(default=15)
    REFRESH_TOKEN_DAYS: int = Field(default=7)
    COOKIE_SECURE: bool = Field(default=False)
    COOKIE_SAMESITE: str = Field(default="lax")
    COOKIE_DOMAIN: Optional[str] = Field(default=None)
    ALLOW_REGISTRATION: bool = Field(default=True)
    PASSWORD_MIN_LENGTH: int = Field(default=10)
    LOGIN_RATE_LIMIT: str = Field(default="5/minute")
    REGISTER_RATE_LIMIT: str = Field(default="10/hour")

    # Upload and folder limits
    MAX_UPLOAD_MB: int = Field(default=25)
    ALLOWED_EXTENSIONS: str = Field(default="pdf")
    USER_STORAGE_QUOTA_MB: int = Field(default=500)
    MAX_FOLDER_DEPTH: int = Field(default=20)
    MAX_NAME_LENGTH: int = Field(default=120)

    # ImageKit
    IMAGEKIT_PRIVATE_KEY: str = Field(default="")
    IMAGEKIT_URL_ENDPOINT: str = Field(default="https://ik.imagekit.io/your_id")
    IMAGEKIT_BASE_FOLDER: str = Field(default="/citegen")
    SIGNED_URL_EXPIRES_SECONDS: int = Field(default=300)

    # Storage Cleaner
    STORAGE_CLEANER_INTERVAL_SECONDS: int = Field(default=30)
    STORAGE_CLEANER_BATCH_SIZE: int = Field(default=100)
    STORAGE_CLEANER_MAX_ATTEMPTS: int = Field(default=10)

    model_config = SettingsConfigDict(
        env_file=(str(ROOT_ENV), str(BACKEND_ENV)),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ALLOW_ORIGINS.split(",") if o.strip()]

    @property
    def allowed_extensions_set(self) -> set[str]:
        return {ext.strip().lower().lstrip(".") for ext in self.ALLOWED_EXTENSIONS.split(",") if ext.strip()}

    def validate_runtime(self) -> None:
        """
        Validates settings at startup according to spec section 2.3.
        Refuses to start with a ValueError if validation fails.
        """
        if not self.JWT_SECRET or len(self.JWT_SECRET) < 32:
            raise ValueError("JWT_SECRET must be set and at least 32 characters long.")

        if self.APP_ENV == "production":
            if not self.COOKIE_SECURE:
                raise ValueError("COOKIE_SECURE must be true when APP_ENV=production.")
            origins = self.cors_origins_list
            if "*" in origins:
                raise ValueError("CORS_ALLOW_ORIGINS cannot contain '*' when credentials are used.")
            for origin in origins:
                if "localhost" in origin or "127.0.0.1" in origin:
                    raise ValueError(f"Production CORS origin cannot contain localhost/127.0.0.1: {origin}")

            # Check ImageKit placeholders in production
            if not self.IMAGEKIT_PRIVATE_KEY or "your_" in self.IMAGEKIT_URL_ENDPOINT:
                raise ValueError("IMAGEKIT_PRIVATE_KEY and IMAGEKIT_URL_ENDPOINT must be configured in production.")

        if self.MAX_UPLOAD_MB <= 0:
            raise ValueError("MAX_UPLOAD_MB must be a positive integer.")
        if self.USER_STORAGE_QUOTA_MB < 0:
            raise ValueError("USER_STORAGE_QUOTA_MB must be non-negative (0 = unlimited).")
        if self.MAX_FOLDER_DEPTH <= 0:
            raise ValueError("MAX_FOLDER_DEPTH must be a positive integer.")
        if self.MAX_NAME_LENGTH <= 0:
            raise ValueError("MAX_NAME_LENGTH must be a positive integer.")


settings = Settings()
