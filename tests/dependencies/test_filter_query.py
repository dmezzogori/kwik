"""Tests for filter query dependency parsing."""

from __future__ import annotations

import pytest

from kwik.dependencies.filter_query import _filters


class TestFilters:
    """Test cases for the _filters function."""

    def test_filters_both_parameters_provided(self) -> None:
        """Test that both filter_key and value provided returns correct dict."""
        result = _filters(filter_key="name", value="john")
        assert result == {"name": "john"}

    def test_filters_filter_key_none_value_provided(self) -> None:
        """Test that None filter_key with value returns empty dict."""
        result = _filters(filter_key=None, value="john")
        assert result == {}

    def test_filters_filter_key_provided_value_none(self) -> None:
        """Test that filter_key with None value returns empty dict."""
        result = _filters(filter_key="name", value=None)
        assert result == {}

    def test_filters_both_parameters_none(self) -> None:
        """Test that both None parameters return empty dict."""
        result = _filters(filter_key=None, value=None)
        assert result == {}

    def test_filters_empty_string_filter_key(self) -> None:
        """Test that empty string filter_key with value returns correct dict."""
        result = _filters(filter_key="", value="john")
        assert result == {"": "john"}

    def test_filters_empty_string_value(self) -> None:
        """Test that filter_key with empty string value returns correct dict."""
        result = _filters(filter_key="name", value="")
        assert result == {"name": ""}

    def test_filters_both_empty_strings(self) -> None:
        """Test that both empty string parameters return correct dict."""
        result = _filters(filter_key="", value="")
        assert result == {"": ""}

    def test_filters_no_parameters(self) -> None:
        """Test that default parameters (None, None) return empty dict."""
        result = _filters()
        assert result == {}

    @pytest.mark.parametrize(
        ("filter_key", "value", "expected"),
        [
            ("status", "active", {"status": "active"}),
            ("type", "user", {"type": "user"}),
            ("category", "premium", {"category": "premium"}),
            ("age", "25", {"age": "25"}),
            ("id", "123", {"id": "123"}),
        ],
    )
    def test_filters_various_valid_combinations(
        self,
        filter_key: str,
        value: str,
        expected: dict[str, str],
    ) -> None:
        """Test various valid filter_key and value combinations."""
        result = _filters(filter_key=filter_key, value=value)
        assert result == expected

    @pytest.mark.parametrize(
        ("filter_key", "value", "expected"),
        [
            (None, "any_value", {}),
            ("any_key", None, {}),
            (None, None, {}),
            (None, "", {}),
            ("", None, {}),
        ],
    )
    def test_filters_none_parameter_combinations(
        self,
        filter_key: str | None,
        value: str | None,
        expected: dict[str, str],
    ) -> None:
        """Test various combinations where at least one parameter is None."""
        result = _filters(filter_key=filter_key, value=value)
        assert result == expected

    def test_filters_special_characters_in_values(self) -> None:
        """Test filter_key and value with special characters."""
        result = _filters(filter_key="search_query", value="user@example.com")
        assert result == {"search_query": "user@example.com"}

        result = _filters(filter_key="tag", value="high-priority")
        assert result == {"tag": "high-priority"}

        result = _filters(filter_key="path", value="/api/v1/users")
        assert result == {"path": "/api/v1/users"}
