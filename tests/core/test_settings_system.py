"""Tests for the simplified settings system."""

from __future__ import annotations

import os

import pytest
from pydantic import field_validator

from kwik.core.settings import BaseKwikSettings, get_settings


class CustomSettingsExample(BaseKwikSettings):
    """Custom settings class for testing extensibility."""

    CUSTOM_SETTING: str = "default_value"
    CUSTOM_INT_SETTING: int = 42
    CUSTOM_BOOL_SETTING: bool = True

    @field_validator("CUSTOM_SETTING")
    @classmethod
    def validate_custom_setting(cls, v: str) -> str:
        """Validate custom setting."""
        if not v:
            msg = "CUSTOM_SETTING cannot be empty"
            raise ValueError(msg)
        return v.upper()


class TestBaseKwikSettings:
    """Test BaseKwikSettings functionality."""

    def test_default_settings_creation(self) -> None:
        """Test creating settings with default values."""
        settings = BaseKwikSettings()
        
        assert settings.PROJECT_NAME == "kwik"
        assert settings.BACKEND_HOST == "localhost"
        assert settings.BACKEND_PORT == 8080
        assert settings.APP_ENV == "development"
        assert settings.DEBUG is True  # Should be True in development
        assert settings.HOTRELOAD is True  # Should be True in development

    def test_settings_from_environment(self) -> None:
        """Test loading settings from environment variables."""
        os.environ["PROJECT_NAME"] = "test_project"
        os.environ["BACKEND_PORT"] = "9000"
        os.environ["DEBUG"] = "false"
        
        try:
            settings = BaseKwikSettings()
            
            assert settings.PROJECT_NAME == "test_project"
            assert settings.BACKEND_PORT == 9000
            assert settings.DEBUG is False
        finally:
            # Clean up
            os.environ.pop("PROJECT_NAME", None)
            os.environ.pop("BACKEND_PORT", None)
            os.environ.pop("DEBUG", None)

    def test_database_uri_construction(self) -> None:
        """Test automatic database URI construction."""
        settings = BaseKwikSettings()
        
        # Should construct URI from components
        expected_uri = "postgresql://postgres:root@db:5432/db"
        assert settings.SQLALCHEMY_DATABASE_URI == expected_uri

    def test_database_uri_from_environment(self) -> None:
        """Test database URI from environment override."""
        os.environ["SQLALCHEMY_DATABASE_URI"] = "postgresql://custom:pass@host:5432/mydb"
        
        try:
            settings = BaseKwikSettings()
            assert settings.SQLALCHEMY_DATABASE_URI == "postgresql://custom:pass@host:5432/mydb"
        finally:
            os.environ.pop("SQLALCHEMY_DATABASE_URI", None)

    def test_cors_origins_parsing(self) -> None:
        """Test CORS origins parsing from string."""
        os.environ["BACKEND_CORS_ORIGINS"] = '["http://localhost:3000", "http://localhost:3001"]'
        
        try:
            settings = BaseKwikSettings()
            # Check that URLs are parsed correctly (as AnyHttpUrl objects)
            assert len(settings.BACKEND_CORS_ORIGINS) == 2
            assert str(settings.BACKEND_CORS_ORIGINS[0]) == "http://localhost:3000/"
            assert str(settings.BACKEND_CORS_ORIGINS[1]) == "http://localhost:3001/"
        finally:
            os.environ.pop("BACKEND_CORS_ORIGINS", None)

    def test_production_environment_disables_debug_and_hotreload(self) -> None:
        """Test production environment automatically disables debug and hotreload."""
        os.environ["APP_ENV"] = "production"
        
        try:
            settings = BaseKwikSettings()
            assert settings.APP_ENV == "production"
            assert settings.DEBUG is False
            assert settings.HOTRELOAD is False
        finally:
            os.environ.pop("APP_ENV", None)

    def test_multiple_workers_disables_hotreload(self) -> None:
        """Test multiple workers disables hotreload."""
        os.environ["BACKEND_WORKERS"] = "4"
        
        try:
            settings = BaseKwikSettings()
            assert settings.BACKEND_WORKERS == 4
            assert settings.HOTRELOAD is False
        finally:
            os.environ.pop("BACKEND_WORKERS", None)


class TestGetSettings:
    """Test the get_settings function."""

    def test_get_settings_returns_instance(self) -> None:
        """Test get_settings returns a BaseKwikSettings instance."""
        settings = get_settings()
        assert isinstance(settings, BaseKwikSettings)

    def test_get_settings_returns_same_instance(self) -> None:
        """Test get_settings returns the same cached instance."""
        settings1 = get_settings()
        settings2 = get_settings()
        assert settings1 is settings2

    def test_get_settings_loads_from_environment(self) -> None:
        """Test get_settings loads values from environment."""
        os.environ["PROJECT_NAME"] = "from_env"
        
        try:
            # Clear any cached instance by importing fresh
            import importlib
            from kwik.core import settings
            importlib.reload(settings)
            
            settings_instance = settings.get_settings()
            assert settings_instance.PROJECT_NAME == "from_env"
        finally:
            os.environ.pop("PROJECT_NAME", None)


class TestCustomSettings:
    """Test extending BaseKwikSettings with custom settings."""

    def test_custom_settings_class(self) -> None:
        """Test creating custom settings class."""
        settings = CustomSettingsExample()
        
        assert settings.CUSTOM_SETTING == "DEFAULT_VALUE"  # Validator uppercases
        assert settings.CUSTOM_INT_SETTING == 42
        assert settings.CUSTOM_BOOL_SETTING is True
        # Should still have base settings
        assert settings.PROJECT_NAME == "kwik"

    def test_custom_settings_from_environment(self) -> None:
        """Test custom settings loaded from environment."""
        os.environ["CUSTOM_SETTING"] = "from_env"
        os.environ["CUSTOM_INT_SETTING"] = "999"
        
        try:
            settings = CustomSettingsExample()
            
            assert settings.CUSTOM_SETTING == "FROM_ENV"  # Uppercased by validator
            assert settings.CUSTOM_INT_SETTING == 999
        finally:
            os.environ.pop("CUSTOM_SETTING", None)
            os.environ.pop("CUSTOM_INT_SETTING", None)

    def test_custom_settings_validation(self) -> None:
        """Test custom validation in extended settings."""
        os.environ["CUSTOM_SETTING"] = ""
        
        try:
            with pytest.raises(ValueError, match="CUSTOM_SETTING cannot be empty"):
                CustomSettingsExample()
        finally:
            os.environ.pop("CUSTOM_SETTING", None)


class TestExtensibilityExamples:
    """Test realistic extensibility examples."""

    def test_feature_flags_extension(self) -> None:
        """Test adding feature flags to settings."""
        
        class FeatureFlagSettings(BaseKwikSettings):
            FEATURE_X_ENABLED: bool = False
            FEATURE_Y_ENABLED: bool = True
            NEW_UI_ENABLED: bool = False

        os.environ["FEATURE_X_ENABLED"] = "true"
        os.environ["NEW_UI_ENABLED"] = "true"
        
        try:
            settings = FeatureFlagSettings()
            
            assert settings.FEATURE_X_ENABLED is True
            assert settings.FEATURE_Y_ENABLED is True  # Default
            assert settings.NEW_UI_ENABLED is True
            # Still has base framework settings
            assert settings.PROJECT_NAME == "kwik"
        finally:
            os.environ.pop("FEATURE_X_ENABLED", None)
            os.environ.pop("NEW_UI_ENABLED", None)

    def test_api_configuration_extension(self) -> None:
        """Test adding API configuration settings."""
        
        class APISettings(BaseKwikSettings):
            API_RATE_LIMIT: int = 1000
            API_TIMEOUT: int = 30
            EXTERNAL_SERVICE_URL: str = "https://api.example.com"

            @field_validator("API_RATE_LIMIT")
            @classmethod
            def validate_rate_limit(cls, v: int) -> int:
                if v <= 0:
                    msg = "Rate limit must be positive"
                    raise ValueError(msg)
                return v

        os.environ["API_RATE_LIMIT"] = "5000"
        os.environ["EXTERNAL_SERVICE_URL"] = "https://custom.api.com"
        
        try:
            settings = APISettings()
            
            assert settings.API_RATE_LIMIT == 5000
            assert settings.API_TIMEOUT == 30  # Default
            assert settings.EXTERNAL_SERVICE_URL == "https://custom.api.com"
        finally:
            os.environ.pop("API_RATE_LIMIT", None)
            os.environ.pop("EXTERNAL_SERVICE_URL", None)