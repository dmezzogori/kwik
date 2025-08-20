"""
Simplified and opinionated configuration system for Kwik framework.

This module provides a simple settings system that loads configuration from environment variables.
"""

from __future__ import annotations

import secrets
from typing import Any, Literal

from pydantic import AnyHttpUrl, EmailStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from kwik.logging import LOG_LEVELS  # noqa: TC001


class BaseKwikSettings(BaseSettings):
    """
    Base settings class that users can extend with custom settings.

    This replaces the original Settings class and provides the same functionality
    while allowing users to extend it with their own settings.
    """

    # Framework core settings
    APP_ENV: Literal["production", "development"] = "development"
    BACKEND_HOST: str = "localhost"
    BACKEND_PORT: int = 8080
    API_V1_STR: str = "/api/v1"
    PROTOCOL: str = "http"

    # Security settings
    SECRET_KEY: str = secrets.token_urlsafe(32)
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 10_080  # 7 days
    BACKEND_CORS_ORIGINS: list[AnyHttpUrl] = []

    # Server settings
    BACKEND_WORKERS: int = 1
    HOTRELOAD: bool = False
    DEBUG: bool = False
    LOG_LEVEL: LOG_LEVELS = "INFO"

    # Database settings
    POSTGRES_SERVER: str = "db"
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "root"  # noqa: S105
    POSTGRES_DB: str = "db"
    POSTGRES_PORT: str = "5432"
    POSTGRES_MAX_CONNECTIONS: int = 100
    SQLALCHEMY_DATABASE_URI: str = ""

    # Project settings
    PROJECT_NAME: str = "kwik"

    # File upload settings
    UPLOADS_DIR: str = "./uploads"

    # User settings
    FIRST_SUPERUSER: EmailStr = "admin@example.com"
    FIRST_SUPERUSER_PASSWORD: str = "admin"  # noqa: S105

    @field_validator("BACKEND_WORKERS", mode="before")
    @classmethod
    def get_number_of_workers(cls, v: str | int) -> int:
        """Get the number of workers to use in Uvicorn."""
        if isinstance(v, str):
            v = int(v) if v.isdigit() else 1
        if v:
            return v
        return 1

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: str | list[str]) -> list[str] | str:
        """Parse CORS origins from comma-separated string or return as-is."""
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        if isinstance(v, (list, str)):
            return v
        raise ValueError(v)

    @model_validator(mode="before")
    @classmethod
    def validate_interdependent_fields(cls, values: dict[str, Any]) -> dict[str, Any]:
        """Validate fields that depend on other fields."""
        # Handle HOTRELOAD
        backend_workers = values.get("BACKEND_WORKERS", 1)
        # Convert to int if it's a string
        if isinstance(backend_workers, str):
            backend_workers = int(backend_workers) if backend_workers.isdigit() else 1
        app_env = values.get("APP_ENV", "development")
        hotreload = values.get("HOTRELOAD")

        if backend_workers > 1 or app_env != "development":
            values["HOTRELOAD"] = False
        elif hotreload is None:
            values["HOTRELOAD"] = True

        # Handle DEBUG
        debug = values.get("DEBUG")
        if app_env != "development":
            values["DEBUG"] = False
        elif debug is None:
            values["DEBUG"] = True

        # Handle DATABASE_URI
        db_uri = values.get("SQLALCHEMY_DATABASE_URI")
        if not isinstance(db_uri, str) or not db_uri:
            # Build from components
            port = values.get("POSTGRES_PORT", "5432")
            user = values.get("POSTGRES_USER", "postgres")
            password = values.get("POSTGRES_PASSWORD", "root")
            host = values.get("POSTGRES_SERVER", "db")
            db_name = values.get("POSTGRES_DB", "db")

            # Build PostgreSQL connection string
            port_str = f":{port}" if port else ""
            values["SQLALCHEMY_DATABASE_URI"] = f"postgresql://{user}:{password}@{host}{port_str}/{db_name}"

        return values

    model_config = SettingsConfigDict(
        case_sensitive=True,
        # Allow extra fields to prevent validation errors from environment variables
        # that aren't defined as settings fields
        extra="allow",
        env_prefix="KWIK_",
        env_ignore_empty=True,
    )
