"""Comprehensive tests for hierarchical configuration profiles system."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from kwik.core.profiles import ProfileManager, ProfilesSettingsSource, detect_environment
from kwik.core.settings import configure_kwik, get_settings, reset_settings


class TestEnvironmentDetection:
    """Test environment detection functionality."""

    def test_detect_environment_kwik_env(self) -> None:
        """Test environment detection prioritizes KWIK_ENV."""
        with patch.dict(os.environ, {"KWIK_ENV": "staging", "APP_ENV": "production"}):
            assert detect_environment() == "staging"

    def test_detect_environment_app_env_fallback(self) -> None:
        """Test environment detection falls back to APP_ENV."""
        with patch.dict(os.environ, {"APP_ENV": "production"}, clear=True):
            assert detect_environment() == "production"

    def test_detect_environment_default(self) -> None:
        """Test environment detection defaults to 'development'."""
        with patch.dict(os.environ, {}, clear=True):
            assert detect_environment() == "development"


class TestProfilesSettingsSource:
    """Test ProfilesSettingsSource functionality."""

    def setup_method(self) -> None:
        """Set up test environment with temporary directory."""
        self.temp_dir = tempfile.mkdtemp()
        self.profiles_dir = Path(self.temp_dir) / "config"
        self.profiles_dir.mkdir(exist_ok=True)

    def teardown_method(self) -> None:
        """Clean up test environment."""
        import shutil

        shutil.rmtree(self.temp_dir)

    def _create_config_file(self, name: str, content: dict, format_type: str = "json"):
        """Helper to create configuration files."""
        file_path = self.profiles_dir / f"{name}.{format_type}"

        if format_type == "json":
            file_path.write_text(json.dumps(content, indent=2))
        elif format_type in ["yaml", "yml"]:
            try:
                import yaml

                file_path.write_text(yaml.dump(content))
            except ImportError:
                pytest.skip("PyYAML not available")

        return file_path

    def test_load_single_profile_json(self) -> None:
        """Test loading a single JSON profile."""
        config = {"DATABASE_HOST": "localhost", "DEBUG": True}
        self._create_config_file("base", config)

        source = ProfilesSettingsSource(profiles_dir=self.profiles_dir, environment="production")
        loaded = source.load()

        assert loaded["DATABASE_HOST"] == "localhost"
        assert loaded["DEBUG"] is True

    def test_load_single_profile_yaml(self) -> None:
        """Test loading a single YAML profile."""
        config = {"DATABASE_HOST": "localhost", "DEBUG": True}
        self._create_config_file("base", config, "yaml")

        source = ProfilesSettingsSource(profiles_dir=self.profiles_dir, environment="production")
        loaded = source.load()

        assert loaded["DATABASE_HOST"] == "localhost"
        assert loaded["DEBUG"] is True

    def test_hierarchical_loading_order(self) -> None:
        """Test that profiles load in correct hierarchy: base → environment → local."""
        # Create base config
        base_config = {
            "DATABASE_HOST": "base_host",
            "DATABASE_PORT": 5432,
            "DEBUG": False,
            "FEATURES": {"feature1": True, "feature2": False},
        }
        self._create_config_file("base", base_config)

        # Create environment config that overrides some values
        env_config = {
            "DATABASE_HOST": "prod_host",
            "API_KEY": "prod_key",
            "FEATURES": {"feature2": True, "feature3": True},
        }
        self._create_config_file("production", env_config)

        # Create local config that overrides more values
        local_config = {"DATABASE_HOST": "local_host", "DEBUG": True, "LOCAL_ONLY": "yes"}
        self._create_config_file("local", local_config)

        source = ProfilesSettingsSource(profiles_dir=self.profiles_dir, environment="production")
        loaded = source.load()

        # Verify hierarchy: local overrides production overrides base
        assert loaded["DATABASE_HOST"] == "local_host"  # From local
        assert loaded["DATABASE_PORT"] == 5432  # From base (not overridden)
        assert loaded["DEBUG"] is True  # From local (overridden)
        assert loaded["API_KEY"] == "prod_key"  # From production
        assert loaded["LOCAL_ONLY"] == "yes"  # From local only

        # Verify deep merge of nested dictionaries
        assert loaded["FEATURES"]["feature1"] is True  # From base
        assert loaded["FEATURES"]["feature2"] is True  # From production (overridden)
        assert loaded["FEATURES"]["feature3"] is True  # From production

    def test_environment_specific_loading(self) -> None:
        """Test loading different environment-specific configurations."""
        base_config = {"DATABASE_HOST": "localhost"}
        self._create_config_file("base", base_config)

        dev_config = {"DEBUG": True, "LOG_LEVEL": "DEBUG"}
        self._create_config_file("development", dev_config)

        prod_config = {"DEBUG": False, "LOG_LEVEL": "ERROR"}
        self._create_config_file("production", prod_config)

        # Test development environment
        dev_source = ProfilesSettingsSource(profiles_dir=self.profiles_dir, environment="development")
        dev_loaded = dev_source.load()
        assert dev_loaded["DEBUG"] is True
        assert dev_loaded["LOG_LEVEL"] == "DEBUG"
        assert dev_loaded["DATABASE_HOST"] == "localhost"  # From base

        # Test production environment
        prod_source = ProfilesSettingsSource(profiles_dir=self.profiles_dir, environment="production")
        prod_loaded = prod_source.load()
        assert prod_loaded["DEBUG"] is False
        assert prod_loaded["LOG_LEVEL"] == "ERROR"
        assert prod_loaded["DATABASE_HOST"] == "localhost"  # From base

    def test_missing_profiles_ignored(self) -> None:
        """Test that missing profile files are gracefully ignored."""
        base_config = {"DATABASE_HOST": "localhost"}
        self._create_config_file("base", base_config)

        # Request environment that doesn't exist
        source = ProfilesSettingsSource(profiles_dir=self.profiles_dir, environment="nonexistent")
        loaded = source.load()

        # Should still load base config
        assert loaded["DATABASE_HOST"] == "localhost"

    def test_deep_merge_functionality(self) -> None:
        """Test deep merging of nested configuration dictionaries."""
        base_config = {
            "database": {"host": "localhost", "port": 5432, "options": {"timeout": 30, "retries": 3}},
            "cache": {"redis": {"host": "localhost"}},
        }
        self._create_config_file("base", base_config)

        env_config = {
            "database": {
                "host": "prod.db.com",
                "options": {"timeout": 60},  # Should merge with base options
            },
            "cache": {"redis": {"port": 6379}},  # Should merge with base redis config
        }
        self._create_config_file("production", env_config)

        source = ProfilesSettingsSource(profiles_dir=self.profiles_dir, environment="production")
        loaded = source.load()

        # Verify deep merge
        assert loaded["database"]["host"] == "prod.db.com"  # Overridden
        assert loaded["database"]["port"] == 5432  # From base
        assert loaded["database"]["options"]["timeout"] == 60  # Overridden
        assert loaded["database"]["options"]["retries"] == 3  # From base

        assert loaded["cache"]["redis"]["host"] == "localhost"  # From base
        assert loaded["cache"]["redis"]["port"] == 6379  # From env

    def test_file_extensions_priority(self) -> None:
        """Test that different file extensions are tried in order."""
        config = {"TEST": "json_value"}
        self._create_config_file("base", config, "json")

        # Also create a YAML file - JSON should take priority
        yaml_config = {"TEST": "yaml_value"}
        self._create_config_file("base", yaml_config, "yaml")

        source = ProfilesSettingsSource(profiles_dir=self.profiles_dir, environment="test")
        loaded = source.load()

        # JSON should be loaded first (higher priority in default list)
        assert loaded["TEST"] == "json_value"

    def test_get_loaded_profiles_info(self) -> None:
        """Test getting information about loaded profiles."""
        self._create_config_file("base", {"BASE": True})
        self._create_config_file("production", {"PROD": True})
        # No local file created

        source = ProfilesSettingsSource(profiles_dir=self.profiles_dir, environment="production")
        profiles_info = source.get_loaded_profiles()

        assert profiles_info["base"] is not None
        assert profiles_info["production"] is not None
        assert profiles_info["local"] is None

    def test_priority_property(self) -> None:
        """Test priority property getter and setter."""
        source = ProfilesSettingsSource(profiles_dir=self.profiles_dir)

        # Test default priority
        assert source.priority == 2

        # Test setting priority
        source.priority = 5
        assert source.priority == 5

    def test_repr_string(self) -> None:
        """Test string representation of ProfilesSettingsSource."""
        source = ProfilesSettingsSource(profiles_dir=self.profiles_dir, environment="production")

        repr_str = repr(source)
        assert "ProfilesSettingsSource" in repr_str
        assert "production" in repr_str
        assert str(self.profiles_dir) in repr_str

    def test_invalid_file_format_error(self) -> None:
        """Test error handling for invalid file formats."""
        # Create file with unsupported extension
        invalid_file = self.profiles_dir / "base.txt"
        invalid_file.write_text("invalid content")

        # Force the source to try to load .txt files by including it in extensions
        source = ProfilesSettingsSource(
            profiles_dir=self.profiles_dir,
            file_extensions=["txt"],  # Force it to try loading .txt file
        )

        with pytest.raises(ValueError, match="Unsupported file format"):
            source.load()

    def test_yaml_import_error_handling(self) -> None:
        """Test error handling when PyYAML is not available."""
        self._create_config_file("base", {"TEST": "yaml"}, "yaml")

        source = ProfilesSettingsSource(profiles_dir=self.profiles_dir)

        # Mock yaml import to raise ImportError
        with patch("builtins.__import__", side_effect=ImportError("No module named 'yaml'")):
            with pytest.raises(ImportError, match="PyYAML is required"):
                source.load()


class TestProfileManager:
    """Test ProfileManager utility class."""

    def setup_method(self) -> None:
        """Set up test environment with temporary directory."""
        self.temp_dir = tempfile.mkdtemp()
        self.profiles_dir = Path(self.temp_dir) / "config"
        self.profiles_dir.mkdir(exist_ok=True)

    def teardown_method(self) -> None:
        """Clean up test environment."""
        import shutil

        shutil.rmtree(self.temp_dir)

    def _create_config_file(self, name: str, content: dict | None = None, format_type: str = "json"):
        """Helper to create configuration files."""
        file_path = self.profiles_dir / f"{name}.{format_type}"
        content = content or {"test": True}

        if format_type == "json":
            file_path.write_text(json.dumps(content, indent=2))
        elif format_type in ["yaml", "yml"]:
            try:
                import yaml

                file_path.write_text(yaml.dump(content))
            except ImportError:
                file_path.write_text("test: true")

        return file_path

    def test_list_available_profiles(self) -> None:
        """Test listing available configuration profiles."""
        manager = ProfileManager(self.profiles_dir)

        # Create some profile files
        self._create_config_file("base")  # Should be excluded (special)
        self._create_config_file("local")  # Should be excluded (special)
        self._create_config_file("development")
        self._create_config_file("production")
        self._create_config_file("staging", format_type="yaml")

        profiles = manager.list_available_profiles()

        assert "development" in profiles
        assert "production" in profiles
        assert "staging" in profiles
        assert "base" not in profiles  # Special profile excluded
        assert "local" not in profiles  # Special profile excluded
        assert profiles == sorted(profiles)  # Should be sorted

    def test_list_profiles_empty_directory(self) -> None:
        """Test listing profiles when directory doesn't exist."""
        nonexistent_dir = Path(self.temp_dir) / "nonexistent"
        manager = ProfileManager(nonexistent_dir)

        profiles = manager.list_available_profiles()
        assert profiles == []

    def test_validate_profile_structure_complete(self) -> None:
        """Test profile structure validation with complete setup."""
        manager = ProfileManager(self.profiles_dir)

        # Create recommended files
        self._create_config_file("base")

        with patch("kwik.core.profiles.detect_environment", return_value="production"):
            self._create_config_file("production")

            result = manager.validate_profile_structure()

        assert "base" in result["found"]
        assert "production" in result["found"]
        assert len(result["missing"]) == 0

    def test_validate_profile_structure_missing_files(self) -> None:
        """Test profile structure validation with missing files."""
        manager = ProfileManager(self.profiles_dir)

        with patch("kwik.core.profiles.detect_environment", return_value="production"):
            result = manager.validate_profile_structure()

        assert "base" in result["missing"]
        assert "production" in result["missing"]
        assert len(result["found"]) == 0

    def test_validate_profile_structure_local_warning(self) -> None:
        """Test profile structure validation warns about local files."""
        manager = ProfileManager(self.profiles_dir)

        # Create files including local
        self._create_config_file("base")
        self._create_config_file("local")

        with patch("kwik.core.profiles.detect_environment", return_value="development"):
            self._create_config_file("development")

            result = manager.validate_profile_structure()

        assert "local" in result["found"]
        assert any("gitignore" in warning.lower() for warning in result["warnings"])

    def test_create_profile_template_yaml(self) -> None:
        """Test creating YAML profile template."""
        manager = ProfileManager(self.profiles_dir)

        template_path = manager.create_profile_template("staging", "yaml")

        assert template_path.exists()
        assert template_path.name == "staging.yaml"

        content = template_path.read_text()
        assert "staging" in content.lower()
        assert "Staging Environment Configuration" in content

    def test_create_profile_template_json(self) -> None:
        """Test creating JSON profile template."""
        manager = ProfileManager(self.profiles_dir)

        template_path = manager.create_profile_template("production", "json")

        assert template_path.exists()
        assert template_path.name == "production.json"

        content = template_path.read_text()
        assert "production" in content.lower()

        # Should be valid JSON
        json.loads(content)

    def test_create_profile_template_invalid_format(self) -> None:
        """Test error handling for invalid template format."""
        manager = ProfileManager(self.profiles_dir)

        with pytest.raises(ValueError, match="Unsupported format"):
            manager.create_profile_template("test", "xml")

    def test_create_profile_template_creates_directory(self) -> None:
        """Test that creating template creates directory if needed."""
        nonexistent_dir = Path(self.temp_dir) / "new_config"
        manager = ProfileManager(nonexistent_dir)

        template_path = manager.create_profile_template("test", "yaml")

        assert nonexistent_dir.exists()
        assert template_path.exists()


class TestIntegrationWithKwikSettings:
    """Test integration with Kwik settings system."""

    def setup_method(self) -> None:
        """Set up test environment."""
        reset_settings()
        self.temp_dir = tempfile.mkdtemp()
        self.profiles_dir = Path(self.temp_dir) / "config"
        self.profiles_dir.mkdir(exist_ok=True)

    def teardown_method(self) -> None:
        """Clean up test environment."""
        reset_settings()
        import shutil

        shutil.rmtree(self.temp_dir)

    def _create_config_file(self, name: str, content: dict):
        """Helper to create JSON configuration files."""
        file_path = self.profiles_dir / f"{name}.json"
        file_path.write_text(json.dumps(content, indent=2))
        return file_path

    def test_configure_kwik_with_profiles_enabled(self) -> None:
        """Test configuring Kwik with profiles enabled."""
        # Create profile configs
        base_config = {"PROJECT_NAME": "test-app", "DATABASE_PORT": 5432}
        self._create_config_file("base", base_config)

        prod_config = {"PROJECT_NAME": "prod-app", "DEBUG": False}
        self._create_config_file("production", prod_config)

        # Configure Kwik with profiles enabled
        configure_kwik(profiles_enabled=True, profiles_dir=self.profiles_dir, environment="production")

        settings = get_settings()

        # Should load hierarchical configuration
        assert settings.PROJECT_NAME == "prod-app"  # From production profile
        assert settings.DATABASE_PORT == 5432  # From base profile (not overridden)
        assert settings.DEBUG is False  # From production profile

    def test_profiles_with_environment_variables_priority(self) -> None:
        """Test that environment variables still have highest priority."""
        # Create profile config
        base_config = {"PROJECT_NAME": "from-profile"}
        self._create_config_file("base", base_config)

        # Set environment variable
        with patch.dict(os.environ, {"PROJECT_NAME": "from-env"}):
            configure_kwik(profiles_enabled=True, profiles_dir=self.profiles_dir)

            settings = get_settings()

            # Environment variable should override profile
            assert settings.PROJECT_NAME == "from-env"

    def test_profiles_with_config_dict_priority(self) -> None:
        """Test priority order with profiles and config dict."""
        # Create profile config (lowest priority)
        base_config = {"PROJECT_NAME": "from-profile", "DATABASE_PORT": 5432}
        self._create_config_file("base", base_config)

        # Configure with dictionary (medium priority)
        configure_kwik(profiles_enabled=True, profiles_dir=self.profiles_dir, config_dict={"PROJECT_NAME": "from-dict"})

        settings = get_settings()

        # Dict should override profile
        assert settings.PROJECT_NAME == "from-dict"
        # Profile should provide non-overridden values
        assert settings.DATABASE_PORT == 5432

    def test_profiles_disabled_by_default(self) -> None:
        """Test that profiles are disabled by default."""
        # Create profile config that would be loaded if enabled
        base_config = {"PROJECT_NAME": "from-profile"}
        self._create_config_file("base", base_config)

        # Configure without enabling profiles
        configure_kwik()

        settings = get_settings()

        # Should use default value, not from profile
        assert settings.PROJECT_NAME == "kwik"  # Default value

    def test_profiles_with_custom_settings_class(self) -> None:
        """Test profiles work with custom settings classes."""
        from kwik.core.settings import BaseKwikSettings

        class CustomSettings(BaseKwikSettings):
            CUSTOM_FIELD: str = "default"

        # Create profile with custom field
        base_config = {"CUSTOM_FIELD": "from-profile"}
        self._create_config_file("base", base_config)

        configure_kwik(settings_class=CustomSettings, profiles_enabled=True, profiles_dir=self.profiles_dir)

        settings = get_settings()

        assert isinstance(settings, CustomSettings)
        assert settings.CUSTOM_FIELD == "from-profile"
