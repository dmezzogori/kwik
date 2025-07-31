"""Isolated tests for the settings system that don't require database connection."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

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


def test_environment_source_loads_from_env():
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


def test_dict_source_loads_from_dict():
    """Test DictSource loads from dictionary."""
    test_dict = {
        "TEST_SETTING": "dict_value",
        "INT_SETTING": 123,
    }
    
    source = DictSource(test_dict)
    config = source.load()
    
    assert config == test_dict
    assert source.priority == 2


def test_file_source_loads_json():
    """Test FileSource loads from JSON file."""
    test_config = {
        "BACKEND_PORT": 9000,
        "DEBUG": True,
        "PROJECT_NAME": "test_project",
    }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(test_config, f)
        json_file = f.name

    try:
        source = FileSource(json_file)
        config = source.load()
        
        assert config == test_config
        assert source.priority == 3
    finally:
        os.unlink(json_file)


def test_settings_registry_add_source_and_priority_ordering():
    """Test adding sources and priority ordering."""
    registry = SettingsRegistry()
    
    env_source = EnvironmentSource()
    dict_source = DictSource({"TEST": "dict"})
    file_source = FileSource("test.json")
    
    # Add in random order
    registry.add_source(file_source)
    registry.add_source(env_source)
    registry.add_source(dict_source)
    
    # Should be sorted by priority (env=1, dict=2, file=3)
    assert registry._sources[0] == env_source
    assert registry._sources[1] == dict_source
    assert registry._sources[2] == file_source


def test_settings_registry_merged_config():
    """Test configuration merging with priority."""
    registry = SettingsRegistry()
    
    # Add sources with conflicting values
    dict_source1 = DictSource({"SETTING": "low_priority", "UNIQUE1": "value1"})
    dict_source2 = DictSource({"SETTING": "high_priority", "UNIQUE2": "value2"})
    
    # Manually set priorities to test merging
    dict_source1.priority = 3  # Lower priority
    dict_source2.priority = 1  # Higher priority
    
    registry.add_source(dict_source1)
    registry.add_source(dict_source2)
    
    config = registry.get_merged_config()
    
    # High priority should win
    assert config["SETTING"] == "high_priority"
    # Both unique values should be present
    assert config["UNIQUE1"] == "value1"
    assert config["UNIQUE2"] == "value2"


def test_configure_kwik_with_custom_settings():
    """Test configure_kwik with custom settings class."""
    try:
        reset_settings()
        configure_kwik(settings_class=TestCustomSettings)
        settings = get_settings()
        
        assert isinstance(settings, TestCustomSettings)
        assert settings.CUSTOM_SETTING == "DEFAULT_VALUE"  # Validator uppercases
        assert settings.CUSTOM_INT_SETTING == 42
    finally:
        reset_settings()


def test_configure_kwik_with_dict():
    """Test configure_kwik with dictionary."""
    try:
        reset_settings()
        configure_kwik(config_dict={"PROJECT_NAME": "configured_project"})
        settings = get_settings()
        
        assert settings.PROJECT_NAME == "configured_project"
    finally:
        reset_settings()


def test_extensibility_custom_feature_flags():
    """Test adding custom feature flags."""
    class FeatureFlagSettings(BaseKwikSettings):
        FEATURE_X_ENABLED: bool = False
        FEATURE_Y_ENABLED: bool = True
        FEATURE_Z_ROLLOUT_PERCENTAGE: int = 0

    try:
        reset_settings()
        configure_kwik(
            settings_class=FeatureFlagSettings,
            config_dict={
                "FEATURE_X_ENABLED": True,
                "FEATURE_Z_ROLLOUT_PERCENTAGE": 50,
            }
        )

        settings = get_settings()
        assert settings.FEATURE_X_ENABLED is True
        assert settings.FEATURE_Y_ENABLED is True  # Default
        assert settings.FEATURE_Z_ROLLOUT_PERCENTAGE == 50
    finally:
        reset_settings()


def test_priority_ordering_with_env():
    """Test configuration source priority ordering with environment variables."""
    # Set up environment variable (highest priority)
    os.environ["PROJECT_NAME"] = "from_env"
    
    try:
        reset_settings()
        
        config_dict = {"PROJECT_NAME": "from_dict"}
        
        # Configure with dict source
        configure_kwik(config_dict=config_dict)
        
        settings = get_settings()
        
        # Environment should win (highest priority)
        assert settings.PROJECT_NAME == "from_env"
    finally:
        os.environ.pop("PROJECT_NAME", None)
        reset_settings()


def test_multiple_configure_calls():
    """Test multiple configure_kwik calls."""
    try:
        reset_settings()
        
        # First configuration
        configure_kwik(config_dict={"PROJECT_NAME": "first"})
        settings1 = get_settings()
        assert settings1.PROJECT_NAME == "first"
        
        # Second configuration should replace the first
        configure_kwik(config_dict={"PROJECT_NAME": "second"})
        settings2 = get_settings()
        assert settings2.PROJECT_NAME == "second"
    finally:
        reset_settings()


def test_lazy_loading():
    """Test that settings are loaded lazily."""
    try:
        reset_settings()
        
        # Configure before accessing
        configure_kwik(config_dict={"PROJECT_NAME": "lazy_test"})
        
        # First access should load the configured settings
        settings = get_settings()
        assert settings.PROJECT_NAME == "lazy_test"
    finally:
        reset_settings()