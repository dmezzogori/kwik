"""Tests for sorting query dependency parsing."""

from __future__ import annotations

import pytest

from kwik.dependencies.sorting_query import _parse_sorting_query


class TestParseSortingQuery:
    """Test cases for the _parse_sorting_query function."""

    def test_parse_sorting_query_none_input(self) -> None:
        """Test that None input returns empty list."""
        result = _parse_sorting_query(None)
        assert result == []

    def test_parse_sorting_query_empty_string(self) -> None:
        """Test that empty string returns empty list."""
        result = _parse_sorting_query("")
        assert result == []

    def test_parse_sorting_query_single_field_no_direction(self) -> None:
        """Test single field without direction defaults to asc."""
        result = _parse_sorting_query("id")
        assert result == [("id", "asc")]

    def test_parse_sorting_query_single_field_asc(self) -> None:
        """Test single field with explicit asc direction."""
        result = _parse_sorting_query("id:asc")
        assert result == [("id", "asc")]

    def test_parse_sorting_query_single_field_desc(self) -> None:
        """Test single field with desc direction."""
        result = _parse_sorting_query("id:desc")
        assert result == [("id", "desc")]

    def test_parse_sorting_query_multiple_fields_mixed(self) -> None:
        """Test multiple fields with mixed directions."""
        result = _parse_sorting_query("id:desc,name,created_at:asc")
        expected = [("id", "desc"), ("name", "asc"), ("created_at", "asc")]
        assert result == expected

    def test_parse_sorting_query_multiple_fields_all_desc(self) -> None:
        """Test multiple fields all with desc direction."""
        result = _parse_sorting_query("id:desc,name:desc")
        expected = [("id", "desc"), ("name", "desc")]
        assert result == expected

    def test_parse_sorting_query_multiple_fields_no_direction(self) -> None:
        """Test multiple fields without directions default to asc."""
        result = _parse_sorting_query("id,name,created_at")
        expected = [("id", "asc"), ("name", "asc"), ("created_at", "asc")]
        assert result == expected

    def test_parse_sorting_query_invalid_direction_treated_as_field(self) -> None:
        """Test that invalid directions are treated as separate fields due to regex pattern."""
        result = _parse_sorting_query("id:invalid")
        expected = [("id", "asc"), ("invalid", "asc")]
        assert result == expected

    def test_parse_sorting_query_invalid_direction_in_multiple_fields(self) -> None:
        """Test that invalid directions in multiple fields are treated as separate fields."""
        result = _parse_sorting_query("id:desc,name:wrong,created_at:asc")
        expected = [("id", "desc"), ("name", "asc"), ("wrong", "asc"), ("created_at", "asc")]
        assert result == expected

    @pytest.mark.parametrize(
        "field_name",
        [
            "simple_field",
            "field_with_underscores",
            "field123",
            "field_123_test",
            "a",
            "Field",
            "FIELD",
        ],
    )
    def test_parse_sorting_query_various_field_names(self, field_name: str) -> None:
        """Test various valid field names."""
        result = _parse_sorting_query(f"{field_name}:desc")
        assert result == [(field_name, "desc")]

    @pytest.mark.parametrize(
        ("sorting_string", "expected"),
        [
            ("field1:asc,field2:desc,field3", [("field1", "asc"), ("field2", "desc"), ("field3", "asc")]),
            ("a:desc,b:asc,c:desc,d", [("a", "desc"), ("b", "asc"), ("c", "desc"), ("d", "asc")]),
            ("single", [("single", "asc")]),
            ("single:desc", [("single", "desc")]),
        ],
    )
    def test_parse_sorting_query_parametrized_cases(
        self,
        sorting_string: str,
        expected: list[tuple[str, str]],
    ) -> None:
        """Test various sorting string combinations."""
        result = _parse_sorting_query(sorting_string)
        assert result == expected

    def test_parse_sorting_query_regex_boundary_cases(self) -> None:
        """Test regex pattern edge cases."""
        result = _parse_sorting_query("field1,field2:asc,field3:desc")
        expected = [("field1", "asc"), ("field2", "asc"), ("field3", "desc")]
        assert result == expected

    def test_parse_sorting_query_complex_field_names(self) -> None:
        """Test complex but valid field names."""
        result = _parse_sorting_query("user_id:desc,created_at_timestamp:asc,status_code")
        expected = [
            ("user_id", "desc"),
            ("created_at_timestamp", "asc"),
            ("status_code", "asc"),
        ]
        assert result == expected
