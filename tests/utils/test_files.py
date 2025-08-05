"""Test suite for kwik.utils.files."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import UploadFile

from kwik.utils.files import store_file

TEST_CONTENT = b"test content"
TEST_CONTENT_SIZE = len(TEST_CONTENT)


@pytest.mark.asyncio
@patch("aiofiles.open")
@patch("pathlib.Path.mkdir")
@patch("pathlib.Path.resolve")
async def test_store_file_default_path(
    mock_resolve: MagicMock, mock_mkdir: MagicMock, mock_aio_open: MagicMock
) -> None:
    """Test storing a file in the default path."""
    # Arrange
    mock_resolve.return_value = Path("/uploads")
    mock_file = MagicMock(spec=UploadFile)
    mock_file.read = AsyncMock(side_effect=[TEST_CONTENT, b""])
    mock_file.filename = "test.txt"

    # Mock the async context manager for aiofiles.open
    mock_async_file = AsyncMock()
    mock_aio_open.return_value.__aenter__.return_value = mock_async_file

    # Act
    file_name, file_size = await store_file(in_file=mock_file)

    # Assert
    assert isinstance(file_name, str)
    assert file_size == TEST_CONTENT_SIZE
    mock_aio_open.assert_called_once()
    assert mock_aio_open.call_args[0][0].startswith("/uploads/")
    mock_async_file.write.assert_called_once_with(TEST_CONTENT)
    mock_mkdir.assert_not_called()  # No path provided, so no mkdir


@pytest.mark.asyncio
@patch("aiofiles.open")
@patch("pathlib.Path.mkdir")
@patch("pathlib.Path.resolve")
async def test_store_file_with_subdirectory(
    mock_resolve: MagicMock, mock_mkdir: MagicMock, mock_aio_open: MagicMock
) -> None:
    """Test storing a file in a subdirectory."""
    # Arrange
    base_path = Path("/uploads")
    sub_path = "images"
    full_path = base_path / sub_path
    mock_resolve.side_effect = [base_path, full_path, full_path]

    mock_file = MagicMock(spec=UploadFile)
    mock_file.read = AsyncMock(side_effect=[TEST_CONTENT, b""])
    mock_file.filename = "test.txt"

    mock_async_file = AsyncMock()
    mock_aio_open.return_value.__aenter__.return_value = mock_async_file

    # Act
    file_name, file_size = await store_file(in_file=mock_file, path=sub_path)

    # Assert
    assert isinstance(file_name, str)
    assert file_size == TEST_CONTENT_SIZE
    mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)
    mock_aio_open.assert_called_once()
    assert mock_aio_open.call_args[0][0].startswith(str(full_path))


@pytest.mark.asyncio
@patch("aiofiles.open")
@patch("pathlib.Path.mkdir")
@patch("pathlib.Path.resolve")
async def test_store_file_with_nested_subdirectory(
    mock_resolve: MagicMock, mock_mkdir: MagicMock, mock_aio_open: MagicMock
) -> None:
    """Test storing a file in a nested subdirectory."""
    # Arrange
    base_path = Path("/uploads")
    sub_path = "images/avatars"
    full_path = base_path / sub_path
    mock_resolve.side_effect = [base_path, full_path, full_path]

    mock_file = MagicMock(spec=UploadFile)
    mock_file.read = AsyncMock(side_effect=[TEST_CONTENT, b""])
    mock_file.filename = "test.txt"

    mock_async_file = AsyncMock()
    mock_aio_open.return_value.__aenter__.return_value = mock_async_file

    # Act
    file_name, file_size = await store_file(in_file=mock_file, path=sub_path)

    # Assert
    assert isinstance(file_name, str)
    assert file_size == TEST_CONTENT_SIZE
    mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)
    mock_aio_open.assert_called_once()
    assert mock_aio_open.call_args[0][0].startswith(str(full_path))


@pytest.mark.asyncio
async def test_store_file_invalid_path_empty() -> None:
    """Test that an empty path raises a ValueError."""
    mock_file = MagicMock(spec=UploadFile)
    with pytest.raises(ValueError, match="Invalid path: empty after cleaning"):
        await store_file(in_file=mock_file, path="/")


@pytest.mark.asyncio
@patch("pathlib.Path.resolve")
async def test_store_file_directory_traversal(mock_resolve: MagicMock) -> None:
    """Test that directory traversal is prevented."""
    # Arrange
    mock_resolve.side_effect = [
        Path("/uploads"),
        Path("/etc"),
    ]
    mock_file = MagicMock(spec=UploadFile)

    # Act & Assert
    with pytest.raises(ValueError, match="Invalid path: directory traversal detected"):
        await store_file(in_file=mock_file, path="../../etc")
