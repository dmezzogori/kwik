"""Tests for configuration dry-run validation."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

from kwik.core.dry_run import ConfigDryRunValidator, ValidationLevel, validate_config
from kwik.core.settings import BaseKwikSettings, reset_settings


class TestConfigDryRunValidator:
    """Test the ConfigDryRunValidator class."""

    def setup_method(self) -> None:
        """Set up clean settings for each test."""
        reset_settings()

    def teardown_method(self) -> None:
        """Clean up after each test."""
        reset_settings()

    def test_basic_validation_success(self) -> None:
        """Test basic successful validation."""
        validator = ConfigDryRunValidator()

        config_dict = {
            "PROJECT_NAME": "test-project",
            "SECRET_KEY": "test-secret-key-12345",
            "SQLALCHEMY_DATABASE_URI": "postgresql://user:pass@localhost:5432/test",
        }

        is_valid = validator.validate_configuration(config_dict=config_dict)

        assert is_valid
        assert not validator.has_errors()
        # Should have some info messages
        assert any(result.level == ValidationLevel.INFO for result in validator.results)

    def test_missing_required_fields(self) -> None:
        """Test validation with missing required fields."""
        validator = ConfigDryRunValidator()

        # Empty config should trigger warnings for default values
        is_valid = validator.validate_configuration(config_dict={})

        # Should be valid because defaults are provided, but with warnings
        assert is_valid
        assert validator.has_warnings()

        # Check that default PROJECT_NAME triggers warning
        warning_fields = {result.field for result in validator.results if result.level == ValidationLevel.WARNING}
        assert "PROJECT_NAME" in warning_fields

    def test_invalid_port_number(self) -> None:
        """Test validation with invalid port number."""
        validator = ConfigDryRunValidator()

        config_dict = {
            "PROJECT_NAME": "test-project",
            "SECRET_KEY": "test-secret-key",
            "BACKEND_PORT": 99999,  # Invalid port
        }

        is_valid = validator.validate_configuration(config_dict=config_dict)

        assert not is_valid
        assert validator.has_errors()

        # Should have port validation error
        port_errors = [
            result
            for result in validator.results
            if result.field == "BACKEND_PORT" and result.level == ValidationLevel.ERROR
        ]
        assert len(port_errors) == 1

    def test_production_environment_warnings(self) -> None:
        """Test warnings for production environment."""
        validator = ConfigDryRunValidator()

        config_dict = {
            "PROJECT_NAME": "test-project",
            "SECRET_KEY": "admin",  # Weak secret (will cause error)
            "APP_ENV": "production",
        }

        is_valid = validator.validate_configuration(config_dict=config_dict)

        assert not is_valid  # Should fail due to weak secret key
        assert validator.has_errors()

        # Check for secret key error
        secret_errors = [
            result
            for result in validator.results
            if result.field == "SECRET_KEY" and result.level == ValidationLevel.ERROR
        ]
        assert len(secret_errors) >= 1

    def test_database_uri_warning(self) -> None:
        """Test warning for non-standard database URI."""
        validator = ConfigDryRunValidator()

        config_dict = {
            "PROJECT_NAME": "test-project",
            "SECRET_KEY": "test-secret-key",
            "SQLALCHEMY_DATABASE_URI": "mysql://user:pass@localhost:3306/test",  # Non-postgresql
        }

        is_valid = validator.validate_configuration(config_dict=config_dict)

        assert is_valid  # Should still be valid, just a warning
        assert validator.has_warnings()

        # Check for database URI warning
        db_warnings = [
            result
            for result in validator.results
            if result.field == "SQLALCHEMY_DATABASE_URI" and result.level == ValidationLevel.WARNING
        ]
        assert len(db_warnings) == 1

    def test_custom_settings_class(self) -> None:
        """Test validation with custom settings class."""

        class CustomSettings(BaseKwikSettings):
            CUSTOM_FIELD: str = "default"

        validator = ConfigDryRunValidator()

        config_dict = {"PROJECT_NAME": "custom-test", "SECRET_KEY": "test-secret-key", "CUSTOM_FIELD": "custom-value"}

        is_valid = validator.validate_configuration(settings_class=CustomSettings, config_dict=config_dict)

        assert is_valid

    def test_configuration_file_validation(self) -> None:
        """Test validation with configuration file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            config_data = {"PROJECT_NAME": "file-test", "SECRET_KEY": "file-secret-key", "DEBUG": False}
            json.dump(config_data, f)
            config_file = f.name

        try:
            validator = ConfigDryRunValidator()
            is_valid = validator.validate_configuration(config_file=config_file)

            assert is_valid
        finally:
            Path(config_file).unlink()

    def test_profiles_validation(self) -> None:
        """Test validation with hierarchical profiles."""
        with tempfile.TemporaryDirectory() as temp_dir:
            profiles_dir = Path(temp_dir) / "config"
            profiles_dir.mkdir()

            # Create base profile
            base_config = {"PROJECT_NAME": "profile-test", "SECRET_KEY": "profile-secret"}
            (profiles_dir / "base.json").write_text(json.dumps(base_config))

            validator = ConfigDryRunValidator()
            is_valid = validator.validate_configuration(
                profiles_enabled=True, profiles_dir=str(profiles_dir), environment="development"
            )

            assert is_valid

    def test_secrets_validation_without_providers(self) -> None:
        """Test secrets validation when no providers are available."""
        validator = ConfigDryRunValidator()

        config_dict = {
            "PROJECT_NAME": "secrets-test",
            "SECRET_KEY": "secret://env/SECRET_KEY",  # Secret reference
        }

        is_valid = validator.validate_configuration(config_dict=config_dict, secrets_enabled=True)

        # Should be valid but may have warnings about secrets resolution
        # The settings system falls back to original value when secrets fail
        assert is_valid

        # Should have info about secret references found
        info_messages = [r for r in validator.results if r.level == ValidationLevel.INFO]
        secret_info = [r for r in info_messages if "secret reference" in r.message]
        assert len(secret_info) >= 1

    def test_text_report_format(self) -> None:
        """Test text report formatting."""
        validator = ConfigDryRunValidator()

        # Trigger some validation issues
        validator.validate_configuration(
            config_dict={
                "BACKEND_PORT": 99999,  # Error
                "APP_ENV": "production",
                "DEBUG": True,  # Warning
            }
        )

        report = validator.get_report(format_type="text")

        assert "Configuration Validation Report" in report
        assert "ERRORS:" in report
        assert "WARNINGS:" in report
        assert "SUMMARY:" in report
        assert "❌ FAILED" in report

    def test_json_report_format(self) -> None:
        """Test JSON report formatting."""
        validator = ConfigDryRunValidator()

        config_dict = {"PROJECT_NAME": "json-test", "SECRET_KEY": "json-secret"}

        validator.validate_configuration(config_dict=config_dict)
        report = validator.get_report(format_type="json")

        # Should be valid JSON
        report_data = json.loads(report)
        assert "validation_results" in report_data
        assert "summary" in report_data
        assert isinstance(report_data["validation_results"], list)
        assert report_data["summary"]["passed"] is True

    def test_validate_config_convenience_function(self) -> None:
        """Test the validate_config convenience function."""
        config_dict = {"PROJECT_NAME": "convenience-test", "SECRET_KEY": "convenience-secret"}

        is_valid, report = validate_config(config_dict=config_dict)

        assert is_valid
        assert isinstance(report, str)
        assert "✅ PASSED" in report

    def test_validation_exception_handling(self) -> None:
        """Test that validation handles exceptions gracefully."""
        validator = ConfigDryRunValidator()

        # Test with a malformed JSON config file to trigger parsing exception
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write('{"invalid": json}')  # Invalid JSON
            invalid_config_file = f.name

        try:
            is_valid = validator.validate_configuration(config_file=invalid_config_file)

            assert not is_valid
            assert validator.has_errors()

            # Should have error about configuration validation failure
            config_errors = [
                result for result in validator.results if "Configuration validation failed" in result.message
            ]
            assert len(config_errors) >= 1
        finally:
            Path(invalid_config_file).unlink()


class TestDryRunWithEnvironmentVariables:
    """Test dry-run validation with environment variables."""

    def setup_method(self) -> None:
        """Set up clean settings for each test."""
        reset_settings()

    def teardown_method(self) -> None:
        """Clean up after each test."""
        reset_settings()

    def test_validation_with_env_vars(self) -> None:
        """Test validation using environment variables."""
        with patch.dict(os.environ, {"PROJECT_NAME": "env-test", "SECRET_KEY": "env-secret-key", "DEBUG": "false"}):
            validator = ConfigDryRunValidator()
            is_valid = validator.validate_configuration()

            assert is_valid

    def test_env_file_validation(self) -> None:
        """Test validation with .env file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            f.write("PROJECT_NAME=envfile-test\n")
            f.write("SECRET_KEY=envfile-secret\n")
            f.write("DEBUG=false\n")
            env_file = f.name

        try:
            validator = ConfigDryRunValidator()
            is_valid = validator.validate_configuration(env_file=env_file)

            assert is_valid
        finally:
            Path(env_file).unlink()


class TestDryRunEdgeCases:
    """Test edge cases for dry-run validation."""

    def setup_method(self) -> None:
        """Set up clean settings for each test."""
        reset_settings()

    def teardown_method(self) -> None:
        """Clean up after each test."""
        reset_settings()

    def test_empty_configuration(self) -> None:
        """Test validation with completely empty configuration."""
        validator = ConfigDryRunValidator()
        is_valid = validator.validate_configuration()

        # Should be valid with defaults, but have warnings
        assert is_valid
        assert validator.has_warnings()

    def test_validation_without_results(self) -> None:
        """Test report generation with no validation results."""
        validator = ConfigDryRunValidator()

        # Get report without running validation
        text_report = validator.get_report(format_type="text")
        json_report = validator.get_report(format_type="json")

        assert "No validation results available" in text_report

        # JSON report should still be valid
        json_data = json.loads(json_report)
        assert json_data["validation_results"] == []

    def test_large_configuration(self) -> None:
        """Test validation with large configuration."""
        large_config = {
            "PROJECT_NAME": "large-test",
            "SECRET_KEY": "large-secret-key",
        }

        # Add many additional fields
        for i in range(100):
            large_config[f"EXTRA_FIELD_{i}"] = f"value_{i}"

        validator = ConfigDryRunValidator()
        is_valid = validator.validate_configuration(config_dict=large_config)

        # Should handle large configs without issues
        assert is_valid
