"""Enhanced configuration system for Kwik framework.

This module provides an extensible, multi-source configuration system that allows users
to extend settings classes and configure applications through multiple methods.
"""

from __future__ import annotations

import json
import os
import secrets
from abc import ABC, abstractmethod
from multiprocessing import cpu_count
from pathlib import Path
from typing import Any, ClassVar, TypeVar

from pydantic import AnyHttpUrl, BaseSettings, EmailStr, PostgresDsn, validator

SettingsType = TypeVar("SettingsType", bound="BaseKwikSettings")


class ConfigurationSource(ABC):
    """Abstract base class for configuration sources."""

    @abstractmethod
    def load(self) -> dict[str, Any]:
        """Load configuration data from the source."""

    @property
    @abstractmethod
    def priority(self) -> int:
        """Return the priority of this configuration source (lower = higher priority)."""


class EnvironmentSource(ConfigurationSource):
    """Configuration source that loads from environment variables."""

    def __init__(self, env_file: str | Path | None = None) -> None:
        """Initialize environment source.

        Args:
            env_file: Optional path to .env file to load

        """
        self.env_file = env_file

    def load(self) -> dict[str, Any]:
        """Load configuration from environment variables."""
        config = {}

        # Load from .env file if specified
        if self.env_file and Path(self.env_file).exists():
            with open(self.env_file) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, value = line.split("=", 1)
                        config[key.strip()] = value.strip().strip("\"'")

        # Environment variables override .env file
        config.update(os.environ)
        return config

    @property
    def priority(self) -> int:
        """Environment variables have high priority."""
        return 1


class DictSource(ConfigurationSource):
    """Configuration source that loads from a dictionary."""

    def __init__(self, config_dict: dict[str, Any]) -> None:
        """Initialize dictionary source.

        Args:
            config_dict: Dictionary containing configuration values

        """
        self.config_dict = config_dict

    def load(self) -> dict[str, Any]:
        """Load configuration from dictionary."""
        return self.config_dict.copy()

    @property
    def priority(self) -> int:
        """Dictionary sources have medium priority."""
        return 2


class FileSource(ConfigurationSource):
    """Configuration source that loads from JSON/YAML files."""

    def __init__(self, file_path: str | Path) -> None:
        """Initialize file source.

        Args:
            file_path: Path to configuration file

        """
        self.file_path = Path(file_path)

    def load(self) -> dict[str, Any]:
        """Load configuration from file."""
        if not self.file_path.exists():
            return {}

        with open(self.file_path) as f:
            if self.file_path.suffix.lower() == ".json":
                return json.load(f)
            if self.file_path.suffix.lower() in [".yml", ".yaml"]:
                try:
                    import yaml

                    return yaml.safe_load(f)
                except ImportError as e:
                    msg = "PyYAML is required for YAML configuration files"
                    raise ImportError(msg) from e
            else:
                msg = f"Unsupported file format: {self.file_path.suffix}"
                raise ValueError(msg)

    @property
    def priority(self) -> int:
        """File sources have low priority."""
        return 3


class SettingsRegistry:
    """Registry for managing settings instances and configuration sources."""

    def __init__(self) -> None:
        """Initialize settings registry."""
        self._sources: list[ConfigurationSource] = []
        self._settings_instance: BaseKwikSettings | None = None
        self._settings_class: type[BaseKwikSettings] = BaseKwikSettings

    def add_source(self, source: ConfigurationSource) -> None:
        """Add a configuration source.

        Args:
            source: Configuration source to add

        """
        self._sources.append(source)
        # Sort by priority (lower numbers = higher priority)
        self._sources.sort(key=lambda s: s.priority)

    def set_settings_class(self, settings_class: type[SettingsType]) -> None:
        """Set the settings class to use.

        Args:
            settings_class: Settings class to use for creating instances

        """
        self._settings_class = settings_class
        # Clear cached instance when class changes
        self._settings_instance = None

    def get_merged_config(self) -> dict[str, Any]:
        """Get merged configuration from all sources."""
        merged_config = {}

        # Merge configurations from all sources (higher priority sources override lower)
        # Sources are already sorted by priority
        for source in reversed(self._sources):  # Start with lowest priority
            config = source.load()
            merged_config.update(config)

        return merged_config

    def get_settings_instance(self) -> BaseKwikSettings:
        """Get or create settings instance."""
        if self._settings_instance is None:
            config = self.get_merged_config()

            # Create instance with merged configuration
            # Use _env_file=None to prevent BaseSettings from loading .env automatically
            # since we handle that through our sources
            self._settings_instance = self._settings_class(_env_file=None, **config)

        return self._settings_instance

    def reset(self) -> None:
        """Reset the registry (useful for testing)."""
        self._sources.clear()
        self._settings_instance = None
        self._settings_class = BaseKwikSettings


class AlternateDBSettings(BaseSettings):
    """Alternate DB settings."""

    ALTERNATE_SQLALCHEMY_DATABASE_URI: str | None = None
    ENABLE_SOFT_DELETE: bool = False


class BaseKwikSettings(BaseSettings):
    """Base settings class that users can extend with custom settings.

    This replaces the original Settings class and provides the same functionality
    while allowing users to extend it with their own settings.
    """

    # Framework core settings
    APP_ENV: str = "development"
    SERVER_NAME: str = "backend"
    BACKEND_HOST: str = "localhost"
    BACKEND_PORT: int = 8080
    API_V1_STR: str = "/api/v1"
    PROTOCOL: str = "http"

    # Security settings
    SECRET_KEY: str = secrets.token_urlsafe(32)
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8  # 8 days
    SERVER_HOST: AnyHttpUrl = "http://localhost"
    BACKEND_CORS_ORIGINS: list[AnyHttpUrl] = []

    # Server settings
    WEBSOCKET_ENABLED: bool = False
    BACKEND_WORKERS: int = 1
    HOTRELOAD: bool = False
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"

    # Database settings
    POSTGRES_SERVER: str = "db"
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "root"
    POSTGRES_DB: str = "db"
    POSTGRES_MAX_CONNECTIONS: int = 100
    ENABLE_SOFT_DELETE: bool = False
    SQLALCHEMY_DATABASE_URI: PostgresDsn | str | None = None

    # Project settings
    PROJECT_NAME: str = "kwik"

    # User settings
    FIRST_SUPERUSER: EmailStr = "admin@example.com"
    FIRST_SUPERUSER_PASSWORD: str = "admin"
    USERS_OPEN_REGISTRATION: bool = False

    # Feature flags
    DB_LOGGER: bool = True
    TEST_ENV: bool = False
    SENTRY_INTEGRATION_ENABLED: bool = False
    SENTRY_DSN: str = ""
    WEBSERVICE_ENABLED: bool = False
    WEBSERVICE_URL: AnyHttpUrl | str = ""
    WEBSERVICE_USER: str | None = None
    WEBSERVICE_PASSWORD: str | None = None

    # Nested settings
    alternate_db: AlternateDBSettings = AlternateDBSettings()

    # Class-level registry reference for advanced use cases
    _registry: ClassVar[SettingsRegistry | None] = None

    @validator("BACKEND_WORKERS", pre=True)
    def get_number_of_workers(cls, v: int, values: dict[str, Any]) -> int:
        """Get the number of workers to use in Uvicorn."""
        if v:
            return v
        if values.get("APP_ENV") == "development":
            return 1
        return cpu_count() // 2

    @validator("HOTRELOAD", pre=True)
    def get_hotreload(cls, v: bool | None, values: dict[str, Any]) -> bool:
        """Get the hotreload flag."""
        if values.get("BACKEND_WORKERS", 1) > 1:
            return False
        if values.get("APP_ENV") != "development":
            return False
        return v if v is not None else True

    @validator("DEBUG", pre=True)
    def get_debug(cls, v: bool | None, values: dict[str, Any]) -> bool:
        """Get the debug flag."""
        if values.get("APP_ENV") != "development":
            return False
        return v if v is not None else True

    @validator("BACKEND_CORS_ORIGINS", pre=True)
    def assemble_cors_origins(cls, v: str | list[str]) -> list[str] | str:
        """Parse CORS origins from comma-separated string or return as-is."""
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        if isinstance(v, (list, str)):
            return v
        raise ValueError(v)

    @validator("SQLALCHEMY_DATABASE_URI", pre=True)
    def assemble_db_connection(cls, v: str | None, values: dict[str, Any]) -> Any:
        """Build PostgreSQL connection string from individual components."""
        if isinstance(v, str):
            return v
        return PostgresDsn.build(
            scheme="postgresql",
            user=values.get("POSTGRES_USER"),
            password=values.get("POSTGRES_PASSWORD"),
            host=values.get("POSTGRES_SERVER"),
            path=f"/{values.get('POSTGRES_DB') or ''}",
        )

    class Config:
        """Pydantic configuration for Settings."""

        case_sensitive = True
        # Allow extra fields to prevent validation errors from environment variables
        # that aren't defined as settings fields
        extra = "allow"


class SettingsFactory:
    """Factory for creating and managing settings instances."""

    def __init__(self) -> None:
        """Initialize settings factory."""
        self._registry = SettingsRegistry()
        # Add default environment source
        self._registry.add_source(EnvironmentSource())

    def configure(
        self,
        settings_class: type[SettingsType] | None = None,
        config_dict: dict[str, Any] | None = None,
        config_file: str | Path | None = None,
        env_file: str | Path | None = None,
        sources: list[ConfigurationSource] | None = None,
    ) -> None:
        """Configure the settings system.

        Args:
            settings_class: Custom settings class to use
            config_dict: Dictionary of configuration values
            config_file: Path to JSON/YAML configuration file
            env_file: Path to .env file (if different from default)
            sources: List of custom configuration sources

        """
        # Reset registry to clear any previous configuration
        self._registry.reset()

        # Set custom settings class if provided
        if settings_class:
            self._registry.set_settings_class(settings_class)
        else:
            self._registry.set_settings_class(BaseKwikSettings)

        # Add configuration sources in priority order
        if sources:
            for source in sources:
                self._registry.add_source(source)
        else:
            # Add default sources

            # Environment source (highest priority)
            self._registry.add_source(EnvironmentSource(env_file))

            # Dictionary source (medium priority)
            if config_dict:
                self._registry.add_source(DictSource(config_dict))

            # File source (lowest priority)
            if config_file:
                self._registry.add_source(FileSource(config_file))

    def get_settings(self) -> BaseKwikSettings:
        """Get the current settings instance."""
        return self._registry.get_settings_instance()

    def reset(self) -> None:
        """Reset the factory (useful for testing)."""
        self._registry.reset()
        # Re-add default environment source
        self._registry.add_source(EnvironmentSource())


# Global factory instance
_settings_factory = SettingsFactory()


def configure_kwik(
    settings_class: type[SettingsType] | None = None,
    config_dict: dict[str, Any] | None = None,
    config_file: str | Path | None = None,
    env_file: str | Path | None = None,
    sources: list[ConfigurationSource] | None = None,
) -> None:
    """Configure Kwik settings system.

    This function allows users to customize the settings system before using Kwik.

    Args:
        settings_class: Custom settings class that extends BaseKwikSettings
        config_dict: Dictionary of configuration values
        config_file: Path to JSON/YAML configuration file
        env_file: Path to .env file
        sources: List of custom configuration sources

    Examples:
        # Use custom settings class
        class MySettings(BaseKwikSettings):
            CUSTOM_SETTING: str = "default"

        configure_kwik(settings_class=MySettings)

        # Use programmatic configuration
        configure_kwik(config_dict={"BACKEND_PORT": 9000})

        # Use configuration file
        configure_kwik(config_file="config.json")

        # Use custom .env file
        configure_kwik(env_file=".env.production")

    """
    _settings_factory.configure(
        settings_class=settings_class,
        config_dict=config_dict,
        config_file=config_file,
        env_file=env_file,
        sources=sources,
    )


def get_settings() -> BaseKwikSettings:
    """Get the current settings instance.

    This function provides lazy loading of settings - they are only created
    when first accessed.

    Returns:
        Current settings instance

    """
    return _settings_factory.get_settings()


def reset_settings() -> None:
    """Reset settings system (primarily for testing).

    This clears any cached settings and configuration sources,
    returning to the default state.
    """
    _settings_factory.reset()


