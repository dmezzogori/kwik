"""
Settings override context manager for testing.

This module provides utilities for temporarily overriding configuration values
in tests, ensuring clean isolation between test cases.
"""

from __future__ import annotations

import logging
from collections.abc import Generator
from contextlib import contextmanager
from typing import Any
from unittest.mock import patch

from kwik.core.settings import BaseKwikSettings, get_settings, reset_settings

logger = logging.getLogger(__name__)


class SettingsOverrideContext:
    """
    Context manager for temporarily overriding settings values in tests.

    This allows test methods to modify configuration values without affecting
    other tests, providing clean isolation.
    """

    def __init__(self, **overrides: Any) -> None:
        """
        Initialize settings override context.

        Args:
            **overrides: Key-value pairs of settings to override

        Examples:
            with SettingsOverrideContext(DEBUG=True, DATABASE_HOST="test.db"):
                # Settings are temporarily overridden within this block
                settings = get_settings()
                assert settings.DEBUG is True
                assert settings.DATABASE_HOST == "test.db"
            # Settings are restored to original values

        """
        self.overrides = overrides
        self._original_settings: BaseKwikSettings | None = None
        self._original_factory_state: dict[str, Any] = {}

    def __enter__(self) -> BaseKwikSettings:
        """
        Enter the context and apply overrides.

        Returns:
            Settings instance with overrides applied

        """
        # Store current settings instance for restoration
        try:
            self._original_settings = get_settings()
        except Exception:
            self._original_settings = None

        # Import here to avoid circular imports
        from kwik.core.settings import _settings_factory

        # Store original factory state
        self._original_factory_state = {
            "sources": _settings_factory._registry._sources.copy(),
            "settings_instance": _settings_factory._registry._settings_instance,
            "settings_class": _settings_factory._registry._settings_class,
        }

        # Get current merged config to preserve existing values
        current_config = _settings_factory._registry.get_merged_config()

        # Merge our overrides with current config (overrides take precedence)
        merged_config = {**current_config, **self.overrides}

        # Reset settings to clear cached instance
        reset_settings()

        # Import and configure with the merged config
        from kwik.core.settings import configure_kwik

        # Restore the settings class if it was custom
        settings_class = self._original_factory_state.get("settings_class")
        if settings_class and settings_class != BaseKwikSettings:
            configure_kwik(settings_class=settings_class, config_dict=merged_config)
        else:
            configure_kwik(config_dict=merged_config)

        # Get the new settings instance
        new_settings = get_settings()

        logger.debug(f"Applied settings overrides: {self.overrides}")
        return new_settings

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit the context and restore original settings."""
        # Import here to avoid circular imports
        from kwik.core.settings import _settings_factory

        try:
            # Restore original factory state
            _settings_factory._registry._sources = self._original_factory_state["sources"]
            _settings_factory._registry._settings_instance = self._original_factory_state["settings_instance"]
            _settings_factory._registry._settings_class = self._original_factory_state["settings_class"]

            logger.debug("Restored original settings configuration")

        except Exception as e:
            logger.warning(f"Failed to restore settings state: {e}")
            # Fallback: just reset settings
            reset_settings()


@contextmanager
def override_settings(**overrides: Any) -> Generator[BaseKwikSettings, None, None]:
    """
    Context manager function for temporarily overriding settings.

    This is a convenience function that creates and manages a SettingsOverrideContext.

    Args:
        **overrides: Key-value pairs of settings to override

    Yields:
        Settings instance with overrides applied

    Examples:
        with override_settings(DEBUG=True, API_KEY="test-key") as settings:
            assert settings.DEBUG is True
            assert settings.API_KEY == "test-key"
            # Perform test operations...

    """
    with SettingsOverrideContext(**overrides) as settings:
        yield settings


class MockedSettingsContext:
    """
    Advanced context manager that uses mocking for field-level overrides.

    This approach directly patches settings attributes without recreating
    the entire settings instance, which can be more efficient for simple overrides.
    """

    def __init__(self, settings_instance: BaseKwikSettings | None = None, **overrides: Any) -> None:
        """
        Initialize mocked settings context.

        Args:
            settings_instance: Specific settings instance to mock (defaults to current)
            **overrides: Key-value pairs of settings to override

        """
        self.settings_instance = settings_instance
        self.overrides = overrides
        self._patches: list[patch] = []

    def __enter__(self) -> BaseKwikSettings:
        """Enter context and apply mocked overrides."""
        if self.settings_instance is None:
            self.settings_instance = get_settings()

        # Create patches for each override
        for key, value in self.overrides.items():
            if hasattr(self.settings_instance, key):
                patcher = patch.object(self.settings_instance, key, value)
                self._patches.append(patcher)
                patcher.start()
                logger.debug(f"Mocked {key} = {value}")
            else:
                logger.warning(f"Settings attribute '{key}' does not exist, skipping mock")

        return self.settings_instance

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit context and restore original values."""
        for patcher in reversed(self._patches):
            patcher.stop()
        self._patches.clear()
        logger.debug("Restored original settings values")


@contextmanager
def mock_settings(**overrides: Any) -> Generator[BaseKwikSettings, None, None]:
    """
    Context manager function for mocking specific settings attributes.

    This uses unittest.mock.patch to override individual attributes on the
    current settings instance without recreating the entire configuration system.

    Args:
        **overrides: Key-value pairs of settings to mock

    Yields:
        Settings instance with mocked attributes

    Examples:
        with mock_settings(DEBUG=True, SECRET_KEY="test-secret") as settings:
            assert settings.DEBUG is True
            assert settings.SECRET_KEY == "test-secret"
            # Original settings instance is preserved, only specified attrs are mocked

    """
    with MockedSettingsContext(**overrides) as settings:
        yield settings


class TransactionalSettingsContext:
    """
    Transactional context manager that preserves the entire settings configuration.

    This provides the most comprehensive state preservation, including all sources,
    factory configuration, and hot reload state.
    """

    def __init__(self, **overrides: Any) -> None:
        """
        Initialize transactional settings context.

        Args:
            **overrides: Settings overrides to apply

        """
        self.overrides = overrides
        self._backup_state: dict[str, Any] = {}

    def __enter__(self) -> BaseKwikSettings:
        """Enter context with full state backup."""
        from kwik.core.hot_reload import get_hot_reload_manager
        from kwik.core.settings import _settings_factory

        # Create comprehensive backup
        self._backup_state = {
            # Settings factory state
            "registry_sources": [source for source in _settings_factory._registry._sources],
            "registry_settings_instance": _settings_factory._registry._settings_instance,
            "registry_settings_class": _settings_factory._registry._settings_class,
            # Hot reload state
            "hot_reload_enabled": get_hot_reload_manager().enabled,
            "hot_reload_current_settings": get_hot_reload_manager().current_settings,
        }

        # Disable hot reload to prevent interference
        if self._backup_state["hot_reload_enabled"]:
            from kwik.core.hot_reload import disable_hot_reload

            disable_hot_reload()

        # Apply overrides using our standard override mechanism
        with SettingsOverrideContext(**self.overrides) as settings:
            return settings

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit context with full state restoration."""
        from kwik.core.hot_reload import enable_hot_reload, get_hot_reload_manager
        from kwik.core.settings import _settings_factory

        try:
            # Restore registry state
            _settings_factory._registry._sources = self._backup_state["registry_sources"]
            _settings_factory._registry._settings_instance = self._backup_state["registry_settings_instance"]
            _settings_factory._registry._settings_class = self._backup_state["registry_settings_class"]

            # Restore hot reload state
            hot_reload_manager = get_hot_reload_manager()
            hot_reload_manager._current_settings = self._backup_state["hot_reload_current_settings"]

            if self._backup_state["hot_reload_enabled"]:
                enable_hot_reload()

            logger.debug("Fully restored transactional settings state")

        except Exception as e:
            logger.error(f"Failed to restore transactional settings state: {e}")
            # Emergency fallback
            reset_settings()


@contextmanager
def transactional_settings(**overrides: Any) -> Generator[BaseKwikSettings, None, None]:
    """
    Comprehensive transactional context manager for settings overrides.

    This provides the highest level of state preservation and restoration,
    including hot reload state and all configuration sources.

    Args:
        **overrides: Settings overrides to apply

    Yields:
        Settings instance with overrides applied

    Examples:
        with transactional_settings(DATABASE_URI="sqlite:///test.db") as settings:
            # Full configuration state is preserved and restored
            assert "sqlite" in settings.DATABASE_URI
            # Perform complex test operations...

    """
    with TransactionalSettingsContext(**overrides) as settings:
        yield settings


# Convenience functions for common test scenarios


def with_test_database(**additional_overrides: Any):
    """
    Context manager for tests requiring a separate test database.

    Args:
        **additional_overrides: Additional settings to override

    Examples:
        with with_test_database(ENABLE_SOFT_DELETE=True) as settings:
            assert "test" in settings.SQLALCHEMY_DATABASE_URI

    """
    test_overrides = {
        "POSTGRES_DB": "kwik_test",
        "SQLALCHEMY_DATABASE_URI": None,  # Force rebuild from components
        "TEST_ENV": True,
        **additional_overrides,
    }
    return override_settings(**test_overrides)


def with_debug_mode(**additional_overrides: Any):
    """
    Context manager for tests requiring debug mode enabled.

    Args:
        **additional_overrides: Additional settings to override

    """
    debug_overrides = {"DEBUG": True, "LOG_LEVEL": "DEBUG", "APP_ENV": "development", **additional_overrides}
    return override_settings(**debug_overrides)


def with_production_mode(**additional_overrides: Any):
    """
    Context manager for tests simulating production environment.

    Args:
        **additional_overrides: Additional settings to override

    """
    production_overrides = {
        "DEBUG": False,
        "APP_ENV": "production",
        "LOG_LEVEL": "INFO",
        "HOTRELOAD": False,
        **additional_overrides,
    }
    return override_settings(**production_overrides)
