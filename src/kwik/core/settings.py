"""
Enhanced configuration system for Kwik framework.

This module provides an extensible, multi-source configuration system that allows users
to extend settings classes and configure applications through multiple methods.
"""

from __future__ import annotations

import json
import logging
import os
import secrets
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Literal

from pydantic import AnyHttpUrl, ConfigDict, EmailStr, field_validator, model_validator
from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)


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
        """
        Initialize environment source.

        Args:
            env_file: Optional path to .env file to load

        """
        self.env_file = env_file
        self._priority = 1

    def load(self) -> dict[str, Any]:
        """Load configuration from environment variables."""
        config = {}

        # Load from .env file if specified
        if self.env_file and Path(self.env_file).exists():
            with Path(self.env_file).open() as f:
                for line in f:
                    stripped_line = line.strip()
                    if stripped_line and not stripped_line.startswith("#") and "=" in stripped_line:
                        key, value = stripped_line.split("=", 1)
                        config[key.strip()] = value.strip().strip("\"'")

        # Environment variables override .env file
        config.update(os.environ)
        return config

    @property
    def priority(self) -> int:
        """Environment variables have high priority."""
        return self._priority

    @priority.setter
    def priority(self, value: int) -> None:
        """Set the priority for this source."""
        self._priority = value


class DictSource(ConfigurationSource):
    """Configuration source that loads from a dictionary."""

    def __init__(self, config_dict: dict[str, Any]) -> None:
        """
        Initialize dictionary source.

        Args:
            config_dict: Dictionary containing configuration values

        """
        self.config_dict = config_dict
        self._priority = 2

    def load(self) -> dict[str, Any]:
        """Load configuration from dictionary."""
        return self.config_dict.copy()

    @property
    def priority(self) -> int:
        """Dictionary sources have medium priority."""
        return self._priority

    @priority.setter
    def priority(self, value: int) -> None:
        """Set the priority for this source."""
        self._priority = value


class FileSource(ConfigurationSource):
    """Configuration source that loads from JSON/YAML files."""

    def __init__(self, file_path: str | Path) -> None:
        """
        Initialize file source.

        Args:
            file_path: Path to configuration file

        """
        self.file_path = Path(file_path)
        self._priority = 3

    def load(self) -> dict[str, Any]:
        """Load configuration from file."""
        if not self.file_path.exists():
            return {}

        with self.file_path.open() as f:
            if self.file_path.suffix.lower() == ".json":
                return json.load(f)
            if self.file_path.suffix.lower() in [".yml", ".yaml"]:
                try:
                    import yaml  # noqa: PLC0415

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
        return self._priority

    @priority.setter
    def priority(self, value: int) -> None:
        """Set the priority for this source."""
        self._priority = value


class SettingsRegistry:
    """Registry for managing settings instances and configuration sources."""

    def __init__(self) -> None:
        """Initialize settings registry."""
        self._sources: list[ConfigurationSource] = []
        self._settings_instance: BaseKwikSettings | None = None
        self._settings_class: type[BaseKwikSettings] = BaseKwikSettings

    def add_source(self, source: ConfigurationSource) -> None:
        """
        Add a configuration source.

        Args:
            source: Configuration source to add

        """
        self._sources.append(source)
        # Sort by priority (lower numbers = higher priority)
        self._sources.sort(key=lambda s: s.priority)

    def set_settings_class[SettingsType: BaseKwikSettings](self, settings_class: type[SettingsType]) -> None:
        """
        Set the settings class to use.

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


class BaseKwikSettings(BaseSettings):
    """
    Base settings class that users can extend with custom settings.

    This replaces the original Settings class and provides the same functionality
    while allowing users to extend it with their own settings.
    """

    # Framework core settings
    APP_ENV: Literal["production", "development"] = "development"
    SERVER_NAME: str = "backend"
    BACKEND_HOST: str = "localhost"
    BACKEND_PORT: int = 8080
    API_V1_STR: str = "/api/v1"
    PROTOCOL: str = "http"

    # Security settings
    SECRET_KEY: str = secrets.token_urlsafe(32)
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 10_080  # 7 days
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
    POSTGRES_PASSWORD: str = "root"  # noqa: S105
    POSTGRES_DB: str = "db"
    POSTGRES_PORT: str = "5432"
    POSTGRES_MAX_CONNECTIONS: int = 100
    SQLALCHEMY_DATABASE_URI: str

    # Project settings
    PROJECT_NAME: str = "kwik"

    # User settings
    FIRST_SUPERUSER: EmailStr = "admin@example.com"
    FIRST_SUPERUSER_PASSWORD: str = "admin"  # noqa: S105

    @field_validator("BACKEND_WORKERS", mode="before")
    @classmethod
    def get_number_of_workers(cls, v: int) -> int:
        """Get the number of workers to use in Uvicorn."""
        if v:
            return v
        # Note: In v2, we need to access other fields differently
        # For now, return a sensible default - will be revisited
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

    model_config = ConfigDict(
        case_sensitive=True,
        # Allow extra fields to prevent validation errors from environment variables
        # that aren't defined as settings fields
        extra="allow",
    )


class SettingsFactory:
    """Factory for creating and managing settings instances."""

    def __init__(self) -> None:
        """Initialize settings factory."""
        self._registry = SettingsRegistry()
        # Add default environment source
        self._registry.add_source(EnvironmentSource())

    def configure[SettingsType: BaseKwikSettings](
        self,
        settings_class: type[SettingsType] | None = None,
        config_dict: dict[str, Any] | None = None,
        config_file: str | Path | None = None,
        env_file: str | Path | None = None,
        sources: list[ConfigurationSource] | None = None,
        profiles_enabled: bool = False,
        profiles_dir: str | Path = "config",
        environment: str | None = None,
        hot_reload: bool = False,
        hot_reload_paths: list[str | Path] | None = None,
        hot_reload_files: list[str | Path] | None = None,
        secrets_enabled: bool = False,
        secrets_auto_resolve: bool = True,
        cloud_secrets_enabled: bool = False,
    ) -> None:
        """
        Configure the settings system.

        Args:
            settings_class: Custom settings class to use
            config_dict: Dictionary of configuration values
            config_file: Path to JSON/YAML configuration file
            env_file: Path to .env file (if different from default)
            sources: List of custom configuration sources
            profiles_enabled: Enable hierarchical configuration profiles
            profiles_dir: Directory containing profile configuration files
            environment: Override environment detection for profile loading
            hot_reload: Enable hot reloading of configuration files
            hot_reload_paths: Directories to watch for configuration changes
            hot_reload_files: Specific files to watch for configuration changes
            secrets_enabled: Enable automatic secrets resolution in configurations
            secrets_auto_resolve: Automatically resolve secret references in configuration values
            cloud_secrets_enabled: Enable cloud secrets providers (AWS, Azure, GCP)

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

            # Hierarchical profiles source (medium priority)
            if profiles_enabled:
                from kwik.core.profiles import ProfilesSettingsSource  # noqa: PLC0415

                self._registry.add_source(ProfilesSettingsSource(profiles_dir=profiles_dir, environment=environment))

            # File source (lowest priority)
            if config_file:
                self._registry.add_source(FileSource(config_file))

        # Configure hot reloading if enabled
        if hot_reload:
            from kwik.core.hot_reload import configure_hot_reload, enable_hot_reload  # noqa: PLC0415

            # Set up watched paths - include profiles directory if profiles are enabled
            watched_paths = list(hot_reload_paths) if hot_reload_paths else []
            if profiles_enabled:
                watched_paths.append(profiles_dir)

            # Set up watched files
            watched_files = list(hot_reload_files) if hot_reload_files else []
            if config_file:
                watched_files.append(config_file)
            if env_file:
                watched_files.append(env_file)

            configure_hot_reload(
                settings_factory=self,
                watched_paths=watched_paths if watched_paths else None,
                watched_files=watched_files if watched_files else None,
            )
            enable_hot_reload()

        # Configure secrets resolution if enabled
        if secrets_enabled:
            self._setup_secrets_resolution(
                auto_resolve=secrets_auto_resolve,
                cloud_enabled=cloud_secrets_enabled,
            )

    def _setup_secrets_resolution(self, auto_resolve: bool = True, cloud_enabled: bool = False) -> None:
        """
        Set up secrets resolution for the settings system.

        Args:
            auto_resolve: Enable automatic resolution of secrets in configuration
            cloud_enabled: Enable cloud secrets providers

        """
        try:
            from kwik.core.secrets import SecretsResolvingSource, get_secrets_manager  # noqa: PLC0415

            # Set up cloud providers if requested
            if cloud_enabled:
                try:
                    from kwik.core.cloud_secrets import register_cloud_providers  # noqa: PLC0415

                    secrets_manager = get_secrets_manager()
                    register_cloud_providers(secrets_manager)
                except ImportError:
                    logger.warning("Cloud secrets providers requested but dependencies not installed")

            # If auto-resolve is enabled, wrap existing sources with secrets resolution
            if auto_resolve:
                # Wrap all existing sources with secrets resolution
                wrapped_sources = []
                for source in self._registry._sources:
                    wrapped_source = SecretsResolvingSource(source)
                    wrapped_sources.append(wrapped_source)

                # Replace sources with wrapped versions
                self._registry._sources = wrapped_sources

        except ImportError as e:
            logger.warning(f"Secrets system not available: {e}")

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


def configure_kwik[SettingsType: BaseKwikSettings](
    settings_class: type[SettingsType] | None = None,
    config_dict: dict[str, Any] | None = None,
    config_file: str | Path | None = None,
    env_file: str | Path | None = None,
    sources: list[ConfigurationSource] | None = None,
    profiles_enabled: bool = False,
    profiles_dir: str | Path = "config",
    environment: str | None = None,
    hot_reload: bool = False,
    hot_reload_paths: list[str | Path] | None = None,
    hot_reload_files: list[str | Path] | None = None,
    secrets_enabled: bool = False,
    secrets_auto_resolve: bool = True,
    cloud_secrets_enabled: bool = False,
) -> None:
    """
    Configure Kwik settings system.

    This function allows users to customize the settings system before using Kwik.

    Args:
        settings_class: Custom settings class that extends BaseKwikSettings
        config_dict: Dictionary of configuration values
        config_file: Path to JSON/YAML configuration file
        env_file: Path to .env file
        sources: List of custom configuration sources
        profiles_enabled: Enable hierarchical configuration profiles
        profiles_dir: Directory containing profile configuration files
        environment: Override environment detection for profile loading
        hot_reload: Enable hot reloading of configuration files
        hot_reload_paths: Directories to watch for configuration changes
        hot_reload_files: Specific files to watch for configuration changes
        secrets_enabled: Enable automatic secrets resolution in configurations
        secrets_auto_resolve: Automatically resolve secret references in configuration values
        cloud_secrets_enabled: Enable cloud secrets providers (AWS, Azure, GCP)

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

        # Enable hierarchical configuration profiles
        configure_kwik(profiles_enabled=True, profiles_dir="config")

        # Enable hot reloading of configuration files
        configure_kwik(hot_reload=True, hot_reload_paths=["config"])

        # Enable secrets resolution with cloud providers
        configure_kwik(secrets_enabled=True, cloud_secrets_enabled=True)

    """
    _settings_factory.configure(
        settings_class=settings_class,
        config_dict=config_dict,
        config_file=config_file,
        env_file=env_file,
        sources=sources,
        profiles_enabled=profiles_enabled,
        profiles_dir=profiles_dir,
        environment=environment,
        hot_reload=hot_reload,
        hot_reload_paths=hot_reload_paths,
        hot_reload_files=hot_reload_files,
        secrets_enabled=secrets_enabled,
        secrets_auto_resolve=secrets_auto_resolve,
        cloud_secrets_enabled=cloud_secrets_enabled,
    )


def get_settings() -> BaseKwikSettings:
    """
    Get the current settings instance.

    This function provides lazy loading of settings - they are only created
    when first accessed.

    Returns:
        Current settings instance

    """
    return _settings_factory.get_settings()


def reset_settings() -> None:
    """
    Reset settings system (primarily for testing).

    This clears any cached settings and configuration sources,
    returning to the default state.
    """
    _settings_factory.reset()
