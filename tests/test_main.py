"""Tests for the main entry point of the kwik application."""

import sys
from collections.abc import Iterator
from unittest.mock import MagicMock, patch

import pytest
from _pytest.monkeypatch import MonkeyPatch

from kwik.__main__ import main


@pytest.fixture
def mock_kwik_run() -> Iterator[MagicMock]:
    """
    Fixture to patch kwik.run.

    Yields:
        The mock object for kwik.run.

    """
    with patch("kwik.run") as mock_run:
        yield mock_run


@pytest.fixture
def mock_kwik_instance() -> Iterator[MagicMock]:
    """
    Fixture to patch kwik.Kwik class.

    Yields:
        The mock object for the kwik.Kwik class.

    """
    with patch("kwik.Kwik") as mock_kwik:
        yield mock_kwik


def test_main_entry_point_with_no_args(
    monkeypatch: MonkeyPatch,
    mock_kwik_run: MagicMock,
    mock_kwik_instance: MagicMock,
) -> None:
    """
    Verify that Kwik is instantiated and run with no CLI arguments.

    When no CLI arguments are provided, Kwik should be instantiated
    with the api_router and passed to kwik.run().
    """
    # Arrange
    monkeypatch.setattr(sys, "argv", ["__main__"])
    # The api_router is imported dynamically, so we patch it where it's loaded from.
    with patch("kwik.api.api.api_router") as mock_api_router:
        # Act
        main()

        # Assert
        mock_kwik_instance.assert_called_once_with(mock_api_router)
        kwik_instance = mock_kwik_instance.return_value
        mock_kwik_run.assert_called_once_with(kwik_instance)


def test_main_entry_point_with_args(
    monkeypatch: MonkeyPatch,
    mock_kwik_run: MagicMock,
    mock_kwik_instance: MagicMock,
) -> None:
    """
    Verify that kwik.run is called with the provided argument.

    When a CLI argument is provided, it should be passed directly
    to kwik.run().
    """
    # Arrange
    app_path = "some.other:app"
    monkeypatch.setattr(sys, "argv", ["__main__", app_path])

    # Act
    main()

    # Assert
    mock_kwik_instance.assert_not_called()
    mock_kwik_run.assert_called_once_with(app_path)
