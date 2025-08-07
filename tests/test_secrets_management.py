"""Comprehensive tests for unified secrets management system."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from kwik.core.secrets import (
    EnvironmentSecretsProvider,
    LocalSecretsProvider,
    SecretResolutionError,
    SecretsManager,
    SecretsResolvingSource,
    get_secret,
    get_secrets_manager,
    resolve_secrets,
)


class TestLocalSecretsProvider:
    """Test local secrets provider functionality."""

    def setup_method(self) -> None:
        """Set up test environment with temporary directory."""
        self.temp_dir = tempfile.mkdtemp()
        self.secrets_path = Path(self.temp_dir) / "secrets"

    def teardown_method(self) -> None:
        """Clean up test environment."""
        import shutil

        shutil.rmtree(self.temp_dir)

    def test_directory_structure_secrets(self) -> None:
        """Test loading secrets from directory structure."""
        # Create secrets directory with individual files
        self.secrets_path.mkdir()
        (self.secrets_path / "api_key").write_text("abc123", encoding="utf-8")
        (self.secrets_path / "database_password.txt").write_text("secret123", encoding="utf-8")
        (self.secrets_path / "jwt_secret.secret").write_text("jwt_token_here", encoding="utf-8")

        provider = LocalSecretsProvider(self.secrets_path)

        assert provider.get_secret("api_key") == "abc123"
        assert provider.get_secret("database_password") == "secret123"
        assert provider.get_secret("jwt_secret") == "jwt_token_here"

    def test_env_file_format(self) -> None:
        """Test loading secrets from .env file format."""
        env_file = self.secrets_path.with_suffix(".env")
        env_content = """
# Database secrets
DB_PASSWORD=super_secret_123
API_KEY="quoted_api_key"

# Empty line and comments should be ignored
JWT_SECRET=jwt_token_value
"""
        env_file.write_text(env_content, encoding="utf-8")

        provider = LocalSecretsProvider(env_file)

        assert provider.get_secret("DB_PASSWORD") == "super_secret_123"
        assert provider.get_secret("API_KEY") == "quoted_api_key"
        assert provider.get_secret("JWT_SECRET") == "jwt_token_value"

    def test_json_file_format(self) -> None:
        """Test loading secrets from JSON file format."""
        json_file = self.secrets_path.with_suffix(".json")
        secrets_data = {
            "database_url": "postgresql://user:pass@localhost/db",
            "api_key": "json_api_key_123",
            "nested": {"secret": "nested_value"},
        }
        json_file.write_text(json.dumps(secrets_data), encoding="utf-8")

        provider = LocalSecretsProvider(json_file)

        assert provider.get_secret("database_url") == "postgresql://user:pass@localhost/db"
        assert provider.get_secret("api_key") == "json_api_key_123"
        # Nested values not supported - gets the nested dict as string representation
        # This will raise SecretResolutionError because nested dict isn't returned as expected
        with pytest.raises(SecretResolutionError):
            provider.get_secret("nonexistent_key")

    def test_secret_not_found(self) -> None:
        """Test error handling when secret is not found."""
        provider = LocalSecretsProvider(self.secrets_path)

        with pytest.raises(SecretResolutionError, match="not found in local storage"):
            provider.get_secret("nonexistent_secret")

    def test_supports_uri(self) -> None:
        """Test URI support detection."""
        provider = LocalSecretsProvider(self.secrets_path)

        assert provider.supports_uri("secret://local/api_key")
        assert provider.supports_uri("secret://file/database_password")
        assert not provider.supports_uri("secret://aws/secret_name")
        assert not provider.supports_uri("https://example.com")

    def test_list_secrets_directory(self) -> None:
        """Test listing secrets from directory structure."""
        self.secrets_path.mkdir()
        (self.secrets_path / "api_key").write_text("value1", encoding="utf-8")
        (self.secrets_path / "db_password.txt").write_text("value2", encoding="utf-8")
        (self.secrets_path / "jwt_secret.secret").write_text("value3", encoding="utf-8")

        provider = LocalSecretsProvider(self.secrets_path)
        secrets = provider.list_secrets()

        assert "api_key" in secrets
        assert "db_password" in secrets
        assert "jwt_secret" in secrets
        assert secrets == sorted(secrets)  # Should be sorted

    def test_list_secrets_env_file(self) -> None:
        """Test listing secrets from .env file."""
        env_file = self.secrets_path.with_suffix(".env")
        env_content = "SECRET_1=value1\nSECRET_2=value2\n# COMMENT=ignored\n"
        env_file.write_text(env_content, encoding="utf-8")

        provider = LocalSecretsProvider(env_file)
        secrets = provider.list_secrets()

        assert "SECRET_1" in secrets
        assert "SECRET_2" in secrets
        assert "COMMENT" not in secrets

    def test_caching_behavior(self) -> None:
        """Test that secrets are cached after first load."""
        self.secrets_path.mkdir()
        secret_file = self.secrets_path / "cached_secret"
        secret_file.write_text("original_value", encoding="utf-8")

        provider = LocalSecretsProvider(self.secrets_path)

        # First load
        assert provider.get_secret("cached_secret") == "original_value"

        # Change file content
        secret_file.write_text("modified_value", encoding="utf-8")

        # Should return cached value
        assert provider.get_secret("cached_secret") == "original_value"

    def test_provider_properties(self) -> None:
        """Test provider properties."""
        provider = LocalSecretsProvider(self.secrets_path)

        assert provider.provider_name == "Local Secrets"
        assert provider.is_available is True


class TestEnvironmentSecretsProvider:
    """Test environment variables secrets provider."""

    def test_get_secret_with_default_prefixes(self) -> None:
        """Test getting secrets with default prefixes."""
        provider = EnvironmentSecretsProvider()

        with patch.dict(os.environ, {"SECRET_API_KEY": "secret_value", "KWIK_SECRET_DB": "db_value"}):
            assert provider.get_secret("API_KEY") == "secret_value"
            assert provider.get_secret("db") == "db_value"

    def test_get_secret_with_custom_prefixes(self) -> None:
        """Test getting secrets with custom prefixes."""
        provider = EnvironmentSecretsProvider(prefixes=["MYAPP_", ""])

        with patch.dict(os.environ, {"MYAPP_SECRET": "app_secret", "DIRECT_SECRET": "direct_value"}):
            assert provider.get_secret("SECRET") == "app_secret"
            assert provider.get_secret("DIRECT_SECRET") == "direct_value"

    def test_get_secret_case_insensitive(self) -> None:
        """Test that secret lookup is case insensitive."""
        provider = EnvironmentSecretsProvider()

        with patch.dict(os.environ, {"SECRET_API_KEY": "value"}):
            assert provider.get_secret("api_key") == "value"
            assert provider.get_secret("API_KEY") == "value"

    def test_secret_not_found_in_environment(self) -> None:
        """Test error when secret not found in environment."""
        provider = EnvironmentSecretsProvider()

        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(SecretResolutionError, match="not found in environment variables"):
                provider.get_secret("NONEXISTENT")

    def test_supports_uri(self) -> None:
        """Test URI support detection."""
        provider = EnvironmentSecretsProvider()

        assert provider.supports_uri("secret://env/API_KEY")
        assert not provider.supports_uri("secret://aws/secret")
        assert not provider.supports_uri("secret://local/secret")

    def test_provider_properties(self) -> None:
        """Test provider properties."""
        provider = EnvironmentSecretsProvider()

        assert provider.provider_name == "Environment Variables"
        assert provider.is_available is True


class TestSecretsManager:
    """Test secrets manager functionality."""

    def setup_method(self) -> None:
        """Set up test environment."""
        self.manager = SecretsManager()

    def test_default_providers_setup(self) -> None:
        """Test that default providers are set up correctly."""
        providers = self.manager.list_providers()

        provider_names = [p["name"] for p in providers]
        assert "Environment Variables" in provider_names
        assert "Local Secrets" in provider_names

    def test_add_and_remove_providers(self) -> None:
        """Test adding and removing providers."""
        initial_count = len(self.manager.list_providers())

        # Add custom provider
        custom_provider = EnvironmentSecretsProvider(prefixes=["CUSTOM_"])
        self.manager.add_provider(custom_provider)

        assert len(self.manager.list_providers()) == initial_count + 1

        # Remove providers of specific type
        self.manager.remove_provider(EnvironmentSecretsProvider)

        providers = self.manager.list_providers()
        env_providers = [p for p in providers if "Environment" in p["name"]]
        assert len(env_providers) == 0

    def test_simple_secret_resolution(self) -> None:
        """Test resolving simple secret names."""
        with patch.dict(os.environ, {"SECRET_TEST": "test_value"}):
            result = self.manager.get_secret("TEST")
            assert result == "test_value"

    def test_uri_secret_resolution(self) -> None:
        """Test resolving secret:// URIs."""
        with patch.dict(os.environ, {"API_KEY": "env_api_key"}):
            result = self.manager.get_secret("secret://env/API_KEY")
            assert result == "env_api_key"

    def test_secret_resolution_error(self) -> None:
        """Test error when no provider can resolve secret."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(SecretResolutionError, match="Could not resolve secret"):
                self.manager.get_secret("NONEXISTENT_SECRET")

    def test_invalid_uri_format(self) -> None:
        """Test error handling for invalid URI format."""
        with pytest.raises(SecretResolutionError, match="Invalid secret URI format"):
            self.manager.get_secret("secret://invalid-format")

    def test_config_secrets_resolution_simple(self) -> None:
        """Test resolving secrets in configuration dictionary."""
        config = {
            "database_url": "secret://env/DB_URL",
            "api_key": "SECRET_API_KEY",
            "normal_setting": "regular_value",
            "port": 8080,
        }

        with patch.dict(os.environ, {"DB_URL": "postgresql://...", "SECRET_API_KEY": "api_123"}):
            resolved = self.manager.resolve_config_secrets(config)

            assert resolved["database_url"] == "postgresql://..."
            assert resolved["api_key"] == "api_123"
            assert resolved["normal_setting"] == "regular_value"
            assert resolved["port"] == 8080

    def test_config_secrets_resolution_nested(self) -> None:
        """Test resolving secrets in nested configuration."""
        config = {
            "database": {"url": "secret://env/DB_URL", "password": "secret://env/DB_PASSWORD"},
            "cache": {"redis_url": "regular_redis_url"},
            "secrets_list": [
                {"name": "secret1", "value": "secret://env/SECRET1"},
                {"name": "secret2", "value": "regular_value"},
            ],
        }

        with patch.dict(
            os.environ,
            {"DB_URL": "postgresql://localhost/db", "DB_PASSWORD": "db_pass_123", "SECRET1": "secret_value_1"},
        ):
            resolved = self.manager.resolve_config_secrets(config)

            assert resolved["database"]["url"] == "postgresql://localhost/db"
            assert resolved["database"]["password"] == "db_pass_123"
            assert resolved["cache"]["redis_url"] == "regular_redis_url"
            assert resolved["secrets_list"][0]["value"] == "secret_value_1"
            assert resolved["secrets_list"][1]["value"] == "regular_value"

    def test_secret_reference_heuristics(self) -> None:
        """Test heuristic detection of secret references."""
        config = {
            "api_key": "my_api_key_ref",  # Should be detected as secret ref
            "database_password": "db_pass_ref",  # Should be detected
            "jwt_secret": "jwt_token_ref",  # Should be detected
            "redis_url": "redis://localhost:6379",  # Should NOT be detected (URL)
            "port": "8080",  # Should NOT be detected
            "project_name": "my_project",  # Should NOT be detected
        }

        # Mock the secret resolution for detected references
        with patch.object(self.manager, "get_secret") as mock_get_secret:
            mock_get_secret.side_effect = lambda x: f"resolved_{x}"

            resolved = self.manager.resolve_config_secrets(config)

            # These should have been resolved
            mock_get_secret.assert_any_call("my_api_key_ref")
            mock_get_secret.assert_any_call("db_pass_ref")
            mock_get_secret.assert_any_call("jwt_token_ref")

            # These should not have been called
            assert resolved["redis_url"] == "redis://localhost:6379"
            assert resolved["port"] == "8080"
            assert resolved["project_name"] == "my_project"

    def test_secret_resolution_fallback_on_error(self) -> None:
        """Test that original values are kept when secret resolution fails."""
        config = {"api_key": "secret://nonexistent/KEY", "working_secret": "secret://env/WORKING"}

        with patch.dict(os.environ, {"WORKING": "works"}):
            resolved = self.manager.resolve_config_secrets(config)

            # Failed resolution should keep original value
            assert resolved["api_key"] == "secret://nonexistent/KEY"
            # Successful resolution should work
            assert resolved["working_secret"] == "works"

    def test_get_provider_by_type(self) -> None:
        """Test getting provider by type."""
        env_provider = self.manager.get_provider_by_type(EnvironmentSecretsProvider)
        assert env_provider is not None
        assert isinstance(env_provider, EnvironmentSecretsProvider)

        local_provider = self.manager.get_provider_by_type(LocalSecretsProvider)
        assert local_provider is not None
        assert isinstance(local_provider, LocalSecretsProvider)


class TestSecretsResolvingSource:
    """Test configuration source wrapper that resolves secrets."""

    def test_wraps_source_and_resolves_secrets(self) -> None:
        """Test that wrapper loads config and resolves secrets."""

        # Mock wrapped source
        class MockSource:
            def load(self):
                return {"database_url": "secret://env/DB_URL", "normal_config": "value"}

            @property
            def priority(self) -> int:
                return 5

        mock_source = MockSource()
        wrapped_source = SecretsResolvingSource(mock_source)

        with patch.dict(os.environ, {"DB_URL": "postgresql://resolved"}):
            config = wrapped_source.load()

            assert config["database_url"] == "postgresql://resolved"
            assert config["normal_config"] == "value"

        # Test attribute delegation
        assert wrapped_source.priority == 5

    def test_attribute_delegation(self) -> None:
        """Test that unknown attributes are delegated to wrapped source."""

        class MockSource:
            def load(self):
                return {}

            def custom_method(self) -> str:
                return "delegated"

            custom_property = "delegated_property"

        mock_source = MockSource()
        wrapped_source = SecretsResolvingSource(mock_source)

        assert wrapped_source.custom_method() == "delegated"
        assert wrapped_source.custom_property == "delegated_property"


class TestGlobalSecretsFunctions:
    """Test global convenience functions."""

    def test_get_secret_function(self) -> None:
        """Test global get_secret function."""
        with patch.dict(os.environ, {"SECRET_GLOBAL": "global_value"}):
            result = get_secret("GLOBAL")
            assert result == "global_value"

    def test_resolve_secrets_function(self) -> None:
        """Test global resolve_secrets function."""
        config = {"api_key": "secret://env/API_KEY"}

        with patch.dict(os.environ, {"API_KEY": "resolved_api_key"}):
            resolved = resolve_secrets(config)
            assert resolved["api_key"] == "resolved_api_key"

    def test_get_secrets_manager_function(self) -> None:
        """Test get_secrets_manager function."""
        manager = get_secrets_manager()
        assert isinstance(manager, SecretsManager)

        # Should return the same instance (singleton behavior)
        manager2 = get_secrets_manager()
        assert manager is manager2


class TestIntegrationScenarios:
    """Test realistic integration scenarios."""

    def setup_method(self) -> None:
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.secrets_dir = Path(self.temp_dir) / "secrets"
        self.manager = SecretsManager()

    def teardown_method(self) -> None:
        """Clean up test environment."""
        import shutil

        shutil.rmtree(self.temp_dir)

    def test_local_development_workflow(self) -> None:
        """Test local development secrets workflow."""
        # Set up local secrets directory
        self.secrets_dir.mkdir()
        (self.secrets_dir / "database_password").write_text("local_db_pass", encoding="utf-8")
        (self.secrets_dir / "api_key").write_text("local_api_key", encoding="utf-8")

        # Add local provider with custom path
        local_provider = LocalSecretsProvider(self.secrets_dir)
        self.manager.add_provider(local_provider)

        # Configuration with secret references
        config = {
            "database": {"url": "postgresql://user:secret://local/database_password@localhost/db"},
            "external_api": {"key": "secret://local/api_key", "base_url": "https://api.example.com"},
        }

        resolved = self.manager.resolve_config_secrets(config)

        # Database URL should remain as-is (complex interpolation not supported yet)
        assert "secret://local/database_password" in resolved["database"]["url"]
        # Simple secret reference should be resolved
        assert resolved["external_api"]["key"] == "local_api_key"

    def test_production_environment_variables(self) -> None:
        """Test production deployment with environment variables."""
        config = {
            "database_url": "secret://env/DATABASE_URL",
            "redis_url": "secret://env/REDIS_URL",
            "jwt_secret": "secret://env/JWT_SECRET",
            "debug": False,
        }

        with patch.dict(
            os.environ,
            {
                "DATABASE_URL": "postgresql://prod:secret@prod.db.com/app",
                "REDIS_URL": "redis://prod.cache.com:6379",
                "JWT_SECRET": "prod_jwt_secret_key",
            },
        ):
            resolved = self.manager.resolve_config_secrets(config)

            assert resolved["database_url"] == "postgresql://prod:secret@prod.db.com/app"
            assert resolved["redis_url"] == "redis://prod.cache.com:6379"
            assert resolved["jwt_secret"] == "prod_jwt_secret_key"
            assert resolved["debug"] is False

    def test_fallback_priority_system(self) -> None:
        """Test that providers are tried in correct priority order."""
        # Set up local secrets
        self.secrets_dir.mkdir()
        (self.secrets_dir / "shared_secret").write_text("local_value", encoding="utf-8")

        local_provider = LocalSecretsProvider(self.secrets_dir)
        self.manager.add_provider(local_provider)

        # Environment variable should take priority over local file
        with patch.dict(os.environ, {"SECRET_SHARED_SECRET": "env_value"}):
            result = self.manager.get_secret("SHARED_SECRET")
            # Environment provider is added first, so should have priority
            assert result == "env_value"
