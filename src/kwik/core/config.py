from __future__ import annotations

import secrets
from multiprocessing import cpu_count
from typing import Any, Union

from pydantic import AnyHttpUrl, BaseSettings, EmailStr, PostgresDsn, validator


class AlternateDBSettings(BaseSettings):
    """
    Alternate DB settings.
    """

    ALTERNATE_SQLALCHEMY_DATABASE_URI: str | None = None
    ENABLE_SOFT_DELETE: bool = False


class Settings(BaseSettings):
    APP_ENV: str = "development"
    SERVER_NAME: str = "backend"
    BACKEND_HOST = "localhost"
    BACKEND_PORT = 8080
    API_V1_STR: str = "/api/v1"
    PROTOCOL: str = "http"

    SECRET_KEY: str = secrets.token_urlsafe(32)
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8  # 60 minutes * 24 hours * 8 days = 8 days
    SERVER_HOST: AnyHttpUrl = "http://localhost"
    # BACKEND_CORS_ORIGINS is a JSON-formatted list of origins
    # e.g: '["http://localhost", "http://localhost:4200", "http://localhost:3000", \
    # "http://localhost:8080", "http://local.dockertoolbox.tiangolo.com"]'
    BACKEND_CORS_ORIGINS: list[AnyHttpUrl] = []
    WEBSOCKET_ENABLED = False
    BACKEND_WORKERS: int = 1
    HOTRELOAD: bool = False
    DEBUG: bool = False
    LOG_LEVEL = "INFO"

    @validator("BACKEND_WORKERS", pre=True)
    def get_number_of_workers(cls, v: int, values: dict[str, Any]) -> int:
        """
        Returns the number of workers to use in Uvicorn.
        If the BACKEND_WORKERS environment variable is set, it will return that number.
        If the APP_ENV is set to development, it will default to 1.
        Otherwise, it will return half the number of CPU cores.
        """
        if v:
            return v
        if values.get("APP_ENV") == "development":
            return 1
        return cpu_count() // 2

    @validator("HOTRELOAD", pre=True)
    def get_hotreload(cls, v: bool | None, values: dict[str, Any]) -> bool:
        """
        Returns the hotreload flag.
        If the APP_ENV is set to something else than development, it will return False, ignoring the value of HOTRELOAD.
        """
        if values.get("BACKEND_WORKERS") > 1:
            return False
        if values.get("APP_ENV") != "development":
            return False
        return v if v is not None else True

    @validator("DEBUG", pre=True)
    def get_debug(cls, v: bool | None, values: dict[str, Any]) -> bool:
        """
        Returns the debug flag.
        If the APP_ENV is set to something else than development, it will return False, ignoring the value of DEBUG.
        """
        if values.get("APP_ENV") != "development":
            return False
        return v if v is not None else True

    @validator("BACKEND_CORS_ORIGINS", pre=True)
    def assemble_cors_origins(cls, v: Union[str, list[str]]) -> Union[list[str], str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)

    PROJECT_NAME: str = "kwik"

    POSTGRES_SERVER: str = "db"
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "root"
    POSTGRES_DB: str = "db"
    POSTGRES_MAX_CONNECTIONS: int = 100
    ENABLE_SOFT_DELETE: bool = False
    SQLALCHEMY_DATABASE_URI: PostgresDsn | str | None = None

    @validator("SQLALCHEMY_DATABASE_URI", pre=True)
    def assemble_db_connection(cls, v: str | None, values: dict[str, Any]) -> Any:
        if isinstance(v, str):
            return v
        ret = PostgresDsn.build(
            scheme="postgresql",
            user=values.get("POSTGRES_USER"),
            password=values.get("POSTGRES_PASSWORD"),
            host=values.get("POSTGRES_SERVER"),
            path=f"/{values.get('POSTGRES_DB') or ''}",
        )
        return ret

    alternate_db: AlternateDBSettings = AlternateDBSettings()

    SMTP_HOST: str | None = None
    SMTP_PORT: int | None = None
    SMTP_USER: str | None = None
    SMTP_PASSWORD: str | None = None
    SMTP_TLS: bool = True
    EMAILS_FROM_EMAIL: EmailStr | None = None
    EMAILS_FROM_NAME: str | None = None

    @validator("EMAILS_FROM_NAME")
    def get_project_name(cls, v: str | None, values: dict[str, Any]) -> str:
        if not v:
            return values["PROJECT_NAME"]
        return v

    EMAIL_RESET_TOKEN_EXPIRE_HOURS: int = 48
    EMAIL_TEMPLATES_DIR: str = "/src/app/email-templates"
    EMAILS_ENABLED: bool = False

    @validator("EMAILS_ENABLED", pre=True)
    def get_emails_enabled(cls, v: bool, values: dict[str, Any]) -> bool:
        return bool(values.get("SMTP_HOST") and values.get("SMTP_PORT") and values.get("EMAILS_FROM_EMAIL"))

    FIRST_SUPERUSER: EmailStr = "admin@example.com"
    FIRST_SUPERUSER_PASSWORD: str = "admin"
    USERS_OPEN_REGISTRATION: bool = False

    DB_LOGGER: bool = True

    TEST_ENV: bool = False

    SENTRY_INTEGRATION_ENABLED: bool = False
    SENTRY_DSN: str = ""

    WEBSERVICE_ENABLED: bool = False
    WEBSERVICE_URL: AnyHttpUrl | str = ""
    WEBSERVICE_USER: str | None = None
    WEBSERVICE_PASSWORD: str | None = None

    class Config:
        case_sensitive = True
