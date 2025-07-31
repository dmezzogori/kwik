"""Tests for the new settings system."""

from __future__ import annotations

import json
import os
import tempfile
from typing import Any

import pytest
from pydantic import validator

from kwik.core.settings import (
    BaseKwikSettings,
    DictSource,
    EnvironmentSource,
    FileSource,
    SettingsFactory,
    SettingsRegistry,
    configure_kwik,
    get_settings,
    reset_settings,
)


class TestCustomSettings(BaseKwikSettings):
    """Custom settings class for testing extensibility."""

    CUSTOM_SETTING: str = "default_value"
    CUSTOM_INT_SETTING: int = 42
    CUSTOM_BOOL_SETTING: bool = True

    @validator("CUSTOM_SETTING")
    def validate_custom_setting(cls, v: str) -> str:
        """Validate custom setting."""
        if not v:
            msg = "CUSTOM_SETTING cannot be empty"
            raise ValueError(msg)
        return v.upper()


class TestSettingsSources:
    """Test configuration sources."""

    def test_environment_source_loads_from_env(self):
        """Test EnvironmentSource loads from environment variables."""
        # Set up environment variable
        os.environ["TEST_SETTING"] = "test_value"

        try:
            source = EnvironmentSource()
            config = source.load()

            assert "TEST_SETTING" in config
            assert config["TEST_SETTING"] == "test_value"
            assert source.priority == 1
        finally:
            # Clean up
            os.environ.pop("TEST_SETTING", None)

    def test_environment_source_loads_from_env_file(self):
        """Test EnvironmentSource loads from .env file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            f.write("TEST_SETTING=from_file\n")
            f.write("ANOTHER_SETTING=another_value\n")
            f.write("# Comment line\n")
            f.write('QUOTED_SETTING="quoted value"\n')
            env_file = f.name

        try:
            source = EnvironmentSource(env_file=env_file)
            config = source.load()

            assert config["TEST_SETTING"] == "from_file"
            assert config["ANOTHER_SETTING"] == "another_value"
            assert config["QUOTED_SETTING"] == "quoted value"
        finally:
            os.unlink(env_file)

    def test_dict_source_loads_from_dict(self):
        """Test DictSource loads from dictionary."""
        test_dict = {
            "TEST_SETTING": "dict_value",
            "INT_SETTING": 123,
        }

        source = DictSource(test_dict)
        config = source.load()

        assert config == test_dict
        assert source.priority == 2

    def test_file_source_loads_json(self):
        """Test FileSource loads from JSON file."""
        test_config = {
            "BACKEND_PORT": 9000,
            "DEBUG": True,
            "PROJECT_NAME": "test_project",
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(test_config, f)
            json_file = f.name

        try:
            source = FileSource(json_file)
            config = source.load()

            assert config == test_config
            assert source.priority == 3
        finally:
            os.unlink(json_file)

    def test_file_source_handles_missing_file(self):
        """Test FileSource handles missing files gracefully."""
        source = FileSource("nonexistent.json")
        config = source.load()

        assert config == {}

    def test_file_source_raises_for_unsupported_format(self):
        """Test FileSource raises error for unsupported file formats."""
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
            f.write("test content")
            txt_file = f.name

        try:
            source = FileSource(txt_file)
            with pytest.raises(ValueError, match="Unsupported file format"):
                source.load()
        finally:
            os.unlink(txt_file)


class TestSettingsRegistry:
    """Test settings registry functionality."""

    def setup_method(self):
        """Set up test registry."""
        self.registry = SettingsRegistry()

    def test_add_source_and_priority_ordering(self):
        """Test adding sources and priority ordering."""
        env_source = EnvironmentSource()
        dict_source = DictSource({"TEST": "dict"})
        file_source = FileSource("test.json")

        # Add in random order
        self.registry.add_source(file_source)
        self.registry.add_source(env_source)
        self.registry.add_source(dict_source)

        # Should be sorted by priority (env=1, dict=2, file=3)
        assert self.registry._sources[0] == env_source
        assert self.registry._sources[1] == dict_source
        assert self.registry._sources[2] == file_source

    def test_set_settings_class(self):
        """Test setting custom settings class."""
        self.registry.set_settings_class(TestCustomSettings)
        assert self.registry._settings_class == TestCustomSettings

    def test_get_merged_config(self):
        """Test configuration merging with priority."""
        # Add sources with conflicting values
        dict_source1 = DictSource({"SETTING": "low_priority", "UNIQUE1": "value1"})
        dict_source2 = DictSource({"SETTING": "high_priority", "UNIQUE2": "value2"})

        # Manually set priorities to test merging
        dict_source1.priority = 3  # Lower priority
        dict_source2.priority = 1  # Higher priority

        self.registry.add_source(dict_source1)
        self.registry.add_source(dict_source2)

        config = self.registry.get_merged_config()

        # High priority should win
        assert config["SETTING"] == "high_priority"
        # Both unique values should be present
        assert config["UNIQUE1"] == "value1"
        assert config["UNIQUE2"] == "value2"

    def test_get_settings_instance_caching(self):
        """Test settings instance caching."""
        self.registry.add_source(DictSource({"PROJECT_NAME": "test"}))

        instance1 = self.registry.get_settings_instance()
        instance2 = self.registry.get_settings_instance()

        assert instance1 is instance2  # Same instance
        assert instance1.PROJECT_NAME == "test"

    def test_reset_clears_state(self):
        """Test reset clears registry state."""
        self.registry.add_source(DictSource({"TEST": "value"}))
        self.registry.set_settings_class(TestCustomSettings)

        # Get instance to cache it
        instance = self.registry.get_settings_instance()
        assert instance is not None

        # Reset should clear everything
        self.registry.reset()

        assert len(self.registry._sources) == 0
        assert self.registry._settings_instance is None
        assert self.registry._settings_class == BaseKwikSettings


class TestSettingsFactory:
    """Test settings factory functionality."""

    def setup_method(self):
        """Set up test factory."""
        self.factory = SettingsFactory()

    def teardown_method(self):
        """Clean up after each test."""
        self.factory.reset()

    def test_default_configuration(self):
        """Test factory with default configuration."""
        settings = self.factory.get_settings()

        assert isinstance(settings, BaseKwikSettings)
        assert settings.PROJECT_NAME == "kwik"  # Default value

    def test_configure_with_custom_class(self):
        """Test configuring with custom settings class."""
        self.factory.configure(settings_class=TestCustomSettings)
        settings = self.factory.get_settings()

        assert isinstance(settings, TestCustomSettings)
        assert settings.CUSTOM_SETTING == "DEFAULT_VALUE"  # Validator uppercases
        assert settings.CUSTOM_INT_SETTING == 42

    def test_configure_with_dict(self):
        """Test configuring with dictionary."""
        config = {
            "PROJECT_NAME": "test_project",
            "BACKEND_PORT": 9000,
            "DEBUG": True,
        }

        self.factory.configure(config_dict=config)
        settings = self.factory.get_settings()

        assert settings.PROJECT_NAME == "test_project"
        assert settings.BACKEND_PORT == 9000
        assert settings.DEBUG is True

    def test_configure_with_file(self):
        """Test configuring with file."""
        config = {"PROJECT_NAME": "file_project", "BACKEND_PORT": 8888}

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(config, f)
            config_file = f.name

        try:
            self.factory.configure(config_file=config_file)
            settings = self.factory.get_settings()

            assert settings.PROJECT_NAME == "file_project"
            assert settings.BACKEND_PORT == 8888
        finally:
            os.unlink(config_file)

    def test_priority_ordering(self):
        """Test configuration source priority ordering."""
        # Set up environment variable (highest priority)
        os.environ["TEST_PRIORITY"] = "from_env"

        try:
            config_dict = {"TEST_PRIORITY": "from_dict"}
            config_file_data = {"TEST_PRIORITY": "from_file"}

            with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
                json.dump(config_file_data, f)
                config_file = f.name

            try:
                # Configure with all sources
                self.factory.configure(
                    config_dict=config_dict,
                    config_file=config_file,
                )

                # Create a custom settings class to capture the TEST_PRIORITY value
                class TestPrioritySettings(BaseKwikSettings):
                    TEST_PRIORITY: str = "default"

                self.factory._registry.set_settings_class(TestPrioritySettings)
                settings = self.factory.get_settings()

                # Environment should win (highest priority)
                assert settings.TEST_PRIORITY == "from_env"
            finally:
                os.unlink(config_file)
        finally:
            os.environ.pop("TEST_PRIORITY", None)


class TestConfigureKwikFunction:
    """Test the configure_kwik function."""

    def teardown_method(self):
        """Clean up after each test."""
        reset_settings()

    def test_configure_with_custom_settings(self):
        """Test configure_kwik with custom settings class."""
        configure_kwik(settings_class=TestCustomSettings)
        settings = get_settings()

        assert isinstance(settings, TestCustomSettings)
        assert settings.CUSTOM_SETTING == "DEFAULT_VALUE"

    def test_configure_with_dict(self):
        """Test configure_kwik with dictionary."""
        configure_kwik(config_dict={"PROJECT_NAME": "configured_project"})
        settings = get_settings()

        assert settings.PROJECT_NAME == "configured_project"

    def test_configure_with_env_override(self):
        """Test configure_kwik respects environment variable override."""
        os.environ["PROJECT_NAME"] = "env_project"

        try:
            configure_kwik(config_dict={"PROJECT_NAME": "dict_project"})
            settings = get_settings()

            # Environment should override dictionary
            assert settings.PROJECT_NAME == "env_project"
        finally:
            os.environ.pop("PROJECT_NAME", None)

    def test_multiple_configure_calls(self):
        """Test multiple configure_kwik calls."""
        # First configuration
        configure_kwik(config_dict={"PROJECT_NAME": "first"})
        settings1 = get_settings()
        assert settings1.PROJECT_NAME == "first"

        # Second configuration should replace the first
        configure_kwik(config_dict={"PROJECT_NAME": "second"})
        settings2 = get_settings()
        assert settings2.PROJECT_NAME == "second"


class TestBackwardCompatibility:
    """Test backward compatibility with existing code."""

    def teardown_method(self):
        """Clean up after each test."""
        reset_settings()



class TestExtensibilityUseCases:
    """Test real-world extensibility use cases."""

    def teardown_method(self):
        """Clean up after each test."""
        reset_settings()

    def test_custom_feature_flags(self):
        """Test adding custom feature flags."""
        class FeatureFlagSettings(BaseKwikSettings):
            FEATURE_X_ENABLED: bool = False
            FEATURE_Y_ENABLED: bool = True
            FEATURE_Z_ROLLOUT_PERCENTAGE: int = 0

        configure_kwik(
            settings_class=FeatureFlagSettings,
            config_dict={
                "FEATURE_X_ENABLED": True,
                "FEATURE_Z_ROLLOUT_PERCENTAGE": 50,
            },
        )

        settings = get_settings()
        assert settings.FEATURE_X_ENABLED is True
        assert settings.FEATURE_Y_ENABLED is True  # Default
        assert settings.FEATURE_Z_ROLLOUT_PERCENTAGE == 50

    def test_custom_api_settings(self):
        """Test adding custom API-related settings."""
        class APISettings(BaseKwikSettings):
            API_RATE_LIMIT: int = 1000
            API_TIMEOUT: int = 30
            API_RETRIES: int = 3
            CUSTOM_API_ENDPOINT: str = "https://api.example.com"

            @validator("API_RATE_LIMIT")
            def validate_rate_limit(cls, v: int) -> int:
                if v <= 0:
                    msg = "Rate limit must be positive"
                    raise ValueError(msg)
                return v

        configure_kwik(
            settings_class=APISettings,
            config_dict={"API_RATE_LIMIT": 5000},
        )

        settings = get_settings()
        assert settings.API_RATE_LIMIT == 5000
        assert settings.API_TIMEOUT == 30
        assert settings.CUSTOM_API_ENDPOINT == "https://api.example.com"

    def test_environment_specific_settings(self):
        """Test environment-specific configuration."""
        class EnvironmentSettings(BaseKwikSettings):
            ENVIRONMENT: str = "development"
            CACHE_TTL: int = 300
            LOG_RETENTION_DAYS: int = 7

            @validator("CACHE_TTL")
            def adjust_cache_for_env(cls, v: int, values: dict[str, Any]) -> int:
                env = values.get("ENVIRONMENT", "development")
                if env == "production":
                    return max(v, 3600)  # Minimum 1 hour in production
                return v

        # Test development environment
        configure_kwik(
            settings_class=EnvironmentSettings,
            config_dict={"ENVIRONMENT": "development", "CACHE_TTL": 60},
        )
        dev_settings = get_settings()
        assert dev_settings.CACHE_TTL == 60

        # Reset and test production environment
        reset_settings()
        configure_kwik(
            settings_class=EnvironmentSettings,
            config_dict={"ENVIRONMENT": "production", "CACHE_TTL": 60},
        )
        prod_settings = get_settings()
        assert prod_settings.CACHE_TTL == 3600  # Adjusted by validator
