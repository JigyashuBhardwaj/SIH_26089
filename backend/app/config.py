"""
Application configuration.

Every setting here is read from the environment (see `.env.example` for
the full list and expected format) rather than hardcoded, so no real
credential — database password included — ever lives in source code.

This module owns configuration ONLY. It does not touch the database
(`database.py`) or define any routes (`main.py`) — see the architecture
document's requirement for clear separation between configuration,
database infrastructure, and application startup.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # "development" | "production" — informational only for now; no
    # behavior branches on this yet at this foundation stage.
    app_env: str = "development"

    # PostgreSQL connection string, e.g.:
    # postgresql://<user>:<password>@<host>:<port>/<database>
    # Required — there is no hardcoded fallback, since a real database
    # password must never live in this file.
    database_url: str

    # Comma-separated list of allowed CORS origins for the existing
    # mobile (Expo) and admin (Vite) development clients.
    cors_origins: str = "http://localhost:5173,http://localhost:8081,http://localhost:19006"

    # Phase 5D — JWT authentication configuration.
    #
    # Secret used to sign/verify access tokens (HS256). Required — same
    # "no hardcoded fallback" policy as `database_url` above, since this
    # is exactly the kind of value that must never live in source code.
    jwt_secret_key: str

    # How long an issued access token stays valid. Configurable, with a
    # sensible default (30 minutes) if the environment variable is absent.
    access_token_expire_minutes: int = 30

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def cors_origin_list(self) -> list[str]:
        """`cors_origins` split into a clean list for CORSMiddleware."""
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    """
    Cached settings accessor. Using a function (rather than a module-level
    singleton) keeps this easy to override in tests later via FastAPI's
    dependency-override mechanism, without needing to restructure this
    module when that need arises.
    """
    return Settings()
