"""Tests for settings override context managers."""

from __future__ import annotations

import pytest

from kwik.core.settings import BaseKwikSettings, configure_kwik, get_settings, reset_settings
from kwik.core.test_overrides import (
    MockedSettingsContext,
    SettingsOverrideContext,
    TransactionalSettingsContext,
    mock_settings,
    override_settings,
    transactional_settings,
    with_debug_mode,
    with_production_mode,
    with_test_database,
)


class TestSettingsOverrideContext:
    """Test the basic SettingsOverrideContext."""

    def setup_method(self) -> None:
        """Set up clean settings for each test."""
        reset_settings()

    def teardown_method(self) -> None:
        """Clean up after each test."""
        reset_settings()

    def test_basic_override_functionality(self) -> None:
        """Test basic settings override works correctly."""
        # Get initial settings
        original_settings = get_settings()
        original_project_name = original_settings.PROJECT_NAME
        original_debug = original_settings.DEBUG

        # Override specific values
        with SettingsOverrideContext(PROJECT_NAME="test-override", DEBUG=True) as override_settings:
            assert override_settings.PROJECT_NAME == "test-override"
            assert override_settings.DEBUG is True
            # Non-overridden values should use defaults
            assert override_settings.BACKEND_PORT == 8080

        # After context, settings should be restored
        restored_settings = get_settings()
        assert original_project_name == restored_settings.PROJECT_NAME
        assert original_debug == restored_settings.DEBUG

    def test_multiple_overrides(self) -> None:
        """Test multiple settings can be overridden simultaneously."""
        with SettingsOverrideContext(
            PROJECT_NAME="multi-test", BACKEND_PORT=9999, DEBUG=True, LOG_LEVEL="ERROR", SECRET_KEY="test-secret-key"
        ) as settings:
            assert settings.PROJECT_NAME == "multi-test"
            assert settings.BACKEND_PORT == 9999
            assert settings.DEBUG is True
            assert settings.LOG_LEVEL == "ERROR"
            assert settings.SECRET_KEY == "test-secret-key"

    def test_nested_overrides(self) -> None:
        """Test that nested override contexts work correctly."""
        with SettingsOverrideContext(PROJECT_NAME="outer", DEBUG=False) as outer_settings:
            assert outer_settings.PROJECT_NAME == "outer"
            assert outer_settings.DEBUG is False

            with SettingsOverrideContext(PROJECT_NAME="inner", BACKEND_PORT=7777) as inner_settings:
                assert inner_settings.PROJECT_NAME == "inner"  # Overridden
                assert inner_settings.BACKEND_PORT == 7777  # New override
                # DEBUG should be from parent scope since it's not overridden in inner
                assert inner_settings.DEBUG is False

            # Back to outer context
            restored_outer = get_settings()
            assert restored_outer.PROJECT_NAME == "outer"
            assert restored_outer.DEBUG is False

    def test_custom_settings_class_override(self) -> None:
        """Test overrides work with custom settings classes."""

        class CustomSettings(BaseKwikSettings):
            CUSTOM_FIELD: str = "default-value"
            ANOTHER_FIELD: int = 42

        configure_kwik(settings_class=CustomSettings)

        with SettingsOverrideContext(
            CUSTOM_FIELD="overridden-value", ANOTHER_FIELD=99, PROJECT_NAME="custom-test"
        ) as settings:
            assert isinstance(settings, CustomSettings)
            assert settings.CUSTOM_FIELD == "overridden-value"
            assert settings.ANOTHER_FIELD == 99
            assert settings.PROJECT_NAME == "custom-test"

    def test_exception_handling_in_context(self) -> None:
        """Test that settings are restored even if exception occurs in context."""
        original_name = get_settings().PROJECT_NAME

        try:
            with SettingsOverrideContext(PROJECT_NAME="exception-test") as settings:
                assert settings.PROJECT_NAME == "exception-test"
                raise ValueError("Test exception")
        except ValueError:
            pass  # Expected exception

        # Settings should still be restored
        restored_settings = get_settings()
        assert original_name == restored_settings.PROJECT_NAME


class TestOverrideSettingsFunction:
    """Test the override_settings context manager function."""

    def setup_method(self) -> None:
        """Set up clean settings for each test."""
        reset_settings()

    def teardown_method(self) -> None:
        """Clean up after each test."""
        reset_settings()

    def test_override_settings_function(self) -> None:
        """Test the override_settings convenience function."""
        original_debug = get_settings().DEBUG

        with override_settings(DEBUG=True, PROJECT_NAME="func-test") as settings:
            assert settings.DEBUG is True
            assert settings.PROJECT_NAME == "func-test"

        # Should restore original values
        assert original_debug == get_settings().DEBUG

    def test_override_settings_yields_settings_instance(self) -> None:
        """Test that override_settings yields the correct settings instance."""
        with override_settings(BACKEND_PORT=3333) as settings:
            assert isinstance(settings, BaseKwikSettings)
            assert settings.BACKEND_PORT == 3333
            # Can use the yielded settings instance directly
            assert settings.PROJECT_NAME == "kwik"  # Default value


class TestMockedSettingsContext:
    """Test the MockedSettingsContext for attribute-level mocking."""

    def setup_method(self) -> None:
        """Set up clean settings for each test."""
        reset_settings()

    def teardown_method(self) -> None:
        """Clean up after each test."""
        reset_settings()

    def test_mocked_settings_basic(self) -> None:
        """Test basic attribute mocking functionality."""
        original_settings = get_settings()
        original_debug = original_settings.DEBUG

        with MockedSettingsContext(DEBUG=True, SECRET_KEY="mocked-secret") as mocked_settings:
            # Should be the same instance, just with mocked attributes
            assert mocked_settings is original_settings
            assert mocked_settings.DEBUG is True
            assert mocked_settings.SECRET_KEY == "mocked-secret"

        # After context, original values should be restored
        assert original_debug == original_settings.DEBUG

    def test_mock_settings_function(self) -> None:
        """Test the mock_settings convenience function."""
        with mock_settings(PROJECT_NAME="mocked-project", BACKEND_PORT=4444) as settings:
            assert settings.PROJECT_NAME == "mocked-project"
            assert settings.BACKEND_PORT == 4444

    def test_mock_nonexistent_attribute_warning(self) -> None:
        """Test that mocking nonexistent attributes is handled gracefully."""
        # This should not raise an exception, just log a warning
        with MockedSettingsContext(NONEXISTENT_SETTING="value") as settings:
            # Should not have the nonexistent attribute
            assert not hasattr(settings, "NONEXISTENT_SETTING")


class TestTransactionalSettingsContext:
    """Test the TransactionalSettingsContext for comprehensive state management."""

    def setup_method(self) -> None:
        """Set up clean settings for each test."""
        reset_settings()

    def teardown_method(self) -> None:
        """Clean up after each test."""
        reset_settings()

    def test_transactional_settings_comprehensive(self) -> None:
        """Test that transactional settings preserve complex state."""
        # Set up initial configuration
        configure_kwik(config_dict={"PROJECT_NAME": "initial-project"})
        initial_settings = get_settings()

        with TransactionalSettingsContext(PROJECT_NAME="transactional-test", DEBUG=True) as override_settings:
            assert override_settings.PROJECT_NAME == "transactional-test"
            assert override_settings.DEBUG is True

        # Should restore to initial configuration
        restored_settings = get_settings()
        assert restored_settings.PROJECT_NAME == "initial-project"

    def test_transactional_settings_function(self) -> None:
        """Test the transactional_settings convenience function."""
        with transactional_settings(LOG_LEVEL="CRITICAL", BACKEND_PORT=5555) as settings:
            assert settings.LOG_LEVEL == "CRITICAL"
            assert settings.BACKEND_PORT == 5555


class TestConvenienceFunctions:
    """Test convenience functions for common test scenarios."""

    def setup_method(self) -> None:
        """Set up clean settings for each test."""
        reset_settings()

    def teardown_method(self) -> None:
        """Clean up after each test."""
        reset_settings()

    def test_with_test_database(self) -> None:
        """Test the with_test_database convenience function."""
        with with_test_database() as settings:
            assert settings.POSTGRES_DB == "kwik_test"
            assert settings.TEST_ENV is True
            assert "kwik_test" in settings.SQLALCHEMY_DATABASE_URI

    def test_with_test_database_additional_overrides(self) -> None:
        """Test with_test_database with additional overrides."""
        with with_test_database(ENABLE_SOFT_DELETE=True, POSTGRES_PORT="5433") as settings:
            assert settings.POSTGRES_DB == "kwik_test"
            assert settings.TEST_ENV is True
            assert settings.ENABLE_SOFT_DELETE is True
            assert settings.POSTGRES_PORT == "5433"

    def test_with_debug_mode(self) -> None:
        """Test the with_debug_mode convenience function."""
        with with_debug_mode() as settings:
            assert settings.DEBUG is True
            assert settings.LOG_LEVEL == "DEBUG"
            assert settings.APP_ENV == "development"

    def test_with_production_mode(self) -> None:
        """Test the with_production_mode convenience function."""
        with with_production_mode() as settings:
            assert settings.DEBUG is False
            assert settings.APP_ENV == "production"
            assert settings.LOG_LEVEL == "INFO"
            assert settings.HOTRELOAD is False

    def test_convenience_functions_with_additional_overrides(self) -> None:
        """Test convenience functions accept additional overrides."""
        with with_debug_mode(PROJECT_NAME="debug-test", SECRET_KEY="debug-secret") as settings:
            assert settings.DEBUG is True
            assert settings.PROJECT_NAME == "debug-test"
            assert settings.SECRET_KEY == "debug-secret"


class TestComplexScenarios:
    """Test complex scenarios involving multiple context managers."""

    def setup_method(self) -> None:
        """Set up clean settings for each test."""
        reset_settings()

    def teardown_method(self) -> None:
        """Clean up after each test."""
        reset_settings()

    def test_mixing_different_context_types(self) -> None:
        """Test that different context managers can be used together."""
        # Start with basic override
        with override_settings(PROJECT_NAME="outer-context", DEBUG=False):
            outer_settings = get_settings()
            assert outer_settings.PROJECT_NAME == "outer-context"
            assert outer_settings.DEBUG is False

            # Use mocked settings inside
            with mock_settings(SECRET_KEY="mocked-in-override") as mocked_settings:
                assert mocked_settings.PROJECT_NAME == "outer-context"  # From override
                assert mocked_settings.SECRET_KEY == "mocked-in-override"  # Mocked

    def test_database_override_with_profiles(self) -> None:
        """Test database overrides work correctly with complex configurations."""
        # Configure with some initial settings
        configure_kwik(config_dict={"PROJECT_NAME": "profile-test"})

        with with_test_database(PROJECT_NAME="test-with-db") as settings:
            assert settings.PROJECT_NAME == "test-with-db"
            assert settings.POSTGRES_DB == "kwik_test"
            assert settings.TEST_ENV is True

    def test_override_with_secrets_configuration(self) -> None:
        """Test that overrides work with secrets-enabled configurations."""
        # This test ensures overrides work even with complex factory setups
        try:
            configure_kwik(secrets_enabled=True)
        except ImportError:
            pytest.skip("Secrets system not available")

        with override_settings(PROJECT_NAME="secrets-test", DEBUG=True) as settings:
            assert settings.PROJECT_NAME == "secrets-test"
            assert settings.DEBUG is True

    def test_performance_of_different_approaches(self) -> None:
        """Test that different override approaches work efficiently."""
        import time

        # Test basic override performance
        start_time = time.time()
        for i in range(10):
            with override_settings(PROJECT_NAME=f"test-{i}"):
                pass
        basic_time = time.time() - start_time

        # Test mocked settings performance
        start_time = time.time()
        for i in range(10):
            with mock_settings(PROJECT_NAME=f"mock-{i}"):
                pass
        mock_time = time.time() - start_time

        # Both should complete reasonably quickly (less than 1 second for 10 iterations)
        assert basic_time < 1.0
        assert mock_time < 1.0

        # Mocked settings should generally be faster since it doesn't recreate the settings
        # But we won't assert this since performance can vary


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def setup_method(self) -> None:
        """Set up clean settings for each test."""
        reset_settings()

    def teardown_method(self) -> None:
        """Clean up after each test."""
        reset_settings()

    def test_empty_overrides(self) -> None:
        """Test that empty overrides work correctly."""
        original_settings = get_settings()

        with override_settings() as settings:
            # Should be equivalent to original settings
            assert settings.PROJECT_NAME == original_settings.PROJECT_NAME
            assert settings.DEBUG == original_settings.DEBUG

    def test_none_value_overrides(self) -> None:
        """Test that None values can be used as overrides."""
        with override_settings(SQLALCHEMY_DATABASE_URI=None) as settings:
            # Should force rebuild of database URI from components
            assert settings.SQLALCHEMY_DATABASE_URI is not None
            assert "postgresql://" in settings.SQLALCHEMY_DATABASE_URI

    def test_complex_nested_data_override(self) -> None:
        """Test overriding complex nested configuration data."""

        class ComplexSettings(BaseKwikSettings):
            COMPLEX_CONFIG: dict = {"nested": {"value": "default"}}

        configure_kwik(settings_class=ComplexSettings)

        with override_settings(COMPLEX_CONFIG={"nested": {"value": "overridden", "new_key": "new_value"}}) as settings:
            assert settings.COMPLEX_CONFIG["nested"]["value"] == "overridden"
            assert settings.COMPLEX_CONFIG["nested"]["new_key"] == "new_value"
