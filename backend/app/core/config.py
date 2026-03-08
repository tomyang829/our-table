from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    DATABASE_URL: str = "postgresql+asyncpg://ourtable:ourtable@localhost:5432/ourtable"
    TEST_DATABASE_URL: str = (
        "postgresql+asyncpg://ourtable:ourtable@localhost:5433/ourtable_test"
    )
    SECRET_KEY: str = "changeme"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days

    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GITHUB_CLIENT_ID: str = ""
    GITHUB_CLIENT_SECRET: str = ""

    FRONTEND_URL: str = "http://localhost:5173"

    # Directory for uploaded recipe images (relative to backend root or absolute path)
    UPLOAD_DIR: str = "uploads"

    # Set to True in production (requires HTTPS)
    SECURE_COOKIES: bool = False

    # Set to True for local development to skip OAuth entirely.
    # All API requests will be authenticated as a seeded dev user.
    # NEVER enable this in production.
    DEV_BYPASS_AUTH: bool = False


settings = Settings()

import warnings  # noqa: E402

if settings.SECRET_KEY == "changeme":
    warnings.warn(
        "SECRET_KEY is set to the default 'changeme'. "
        "Set a strong random value in production.",
        stacklevel=1,
    )

if settings.DEV_BYPASS_AUTH:
    warnings.warn(
        "DEV_BYPASS_AUTH is enabled — all requests are authenticated as the dev user. "
        "Never use this in production.",
        stacklevel=1,
    )
