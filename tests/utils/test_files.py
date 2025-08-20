"""Test suite for kwik.utils.files."""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import UploadFile

from kwik.settings import BaseKwikSettings
from kwik.utils.files import store_file

TEST_CONTENT = b"test content"
TEST_CONTENT_SIZE = len(TEST_CONTENT)


@pytest.mark.asyncio
async def test_store_file_default_path() -> None:
    """Test storing a file in the default path."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Arrange
        settings = BaseKwikSettings(UPLOADS_DIR=temp_dir)
        mock_file = MagicMock(spec=UploadFile)
        mock_file.read = AsyncMock(side_effect=[TEST_CONTENT, b""])
        mock_file.filename = "test.txt"

        # Act
        relative_path, file_size = await store_file(in_file=mock_file, settings=settings)

        # Assert
        assert isinstance(relative_path, str)
        assert file_size == TEST_CONTENT_SIZE
        # Should be just the UUID filename since no subpath
        assert "/" not in relative_path

        # Verify file exists and has correct content
        full_path = Path(temp_dir) / relative_path
        assert full_path.exists()
        assert full_path.read_bytes() == TEST_CONTENT


@pytest.mark.asyncio
async def test_store_file_with_subdirectory() -> None:
    """Test storing a file in a subdirectory."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Arrange
        settings = BaseKwikSettings(UPLOADS_DIR=temp_dir)
        sub_path = "images"
        mock_file = MagicMock(spec=UploadFile)
        mock_file.read = AsyncMock(side_effect=[TEST_CONTENT, b""])
        mock_file.filename = "test.txt"

        # Act
        relative_path, file_size = await store_file(in_file=mock_file, path=sub_path, settings=settings)

        # Assert
        assert isinstance(relative_path, str)
        assert file_size == TEST_CONTENT_SIZE
        assert relative_path.startswith(f"{sub_path}/")

        # Verify subdirectory was created and file exists
        full_path = Path(temp_dir) / relative_path
        assert full_path.exists()
        assert full_path.parent.name == sub_path
        assert full_path.read_bytes() == TEST_CONTENT


@pytest.mark.asyncio
async def test_store_file_with_nested_subdirectory() -> None:
    """Test storing a file in a nested subdirectory."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Arrange
        settings = BaseKwikSettings(UPLOADS_DIR=temp_dir)
        sub_path = "images/avatars"
        mock_file = MagicMock(spec=UploadFile)
        mock_file.read = AsyncMock(side_effect=[TEST_CONTENT, b""])
        mock_file.filename = "test.txt"

        # Act
        relative_path, file_size = await store_file(in_file=mock_file, path=sub_path, settings=settings)

        # Assert
        assert isinstance(relative_path, str)
        assert file_size == TEST_CONTENT_SIZE
        assert relative_path.startswith(f"{sub_path}/")

        # Verify nested subdirectory was created and file exists
        full_path = Path(temp_dir) / relative_path
        assert full_path.exists()
        assert str(full_path.parent).endswith("images/avatars")
        assert full_path.read_bytes() == TEST_CONTENT


@pytest.mark.asyncio
async def test_store_file_invalid_path_empty() -> None:
    """Test that an empty path raises a ValueError."""
    with tempfile.TemporaryDirectory() as temp_dir:
        settings = BaseKwikSettings(UPLOADS_DIR=temp_dir)
        mock_file = MagicMock(spec=UploadFile)
        with pytest.raises(ValueError, match="Invalid path: empty after cleaning"):
            await store_file(in_file=mock_file, path="/", settings=settings)


@pytest.mark.asyncio
async def test_store_file_directory_traversal() -> None:
    """Test that directory traversal is prevented."""
    with tempfile.TemporaryDirectory() as temp_dir:
        settings = BaseKwikSettings(UPLOADS_DIR=temp_dir)
        mock_file = MagicMock(spec=UploadFile)

        # Act & Assert - test various traversal attempts
        with pytest.raises(ValueError, match="Invalid path: directory traversal detected"):
            await store_file(in_file=mock_file, path="../../etc", settings=settings)


@pytest.mark.asyncio
async def test_store_file_directory_traversal_with_dots() -> None:
    """Test that directory traversal with different patterns is prevented."""
    with tempfile.TemporaryDirectory() as temp_dir:
        settings = BaseKwikSettings(UPLOADS_DIR=temp_dir)

        # Test various traversal patterns that should be blocked
        dangerous_paths = [
            "../../../etc/passwd",
            "images/../../../etc",
            "valid/../../etc/passwd",
        ]

        for path_attempt in dangerous_paths:
            # Create a fresh mock for each attempt
            mock_file = MagicMock(spec=UploadFile)
            mock_file.read = AsyncMock(side_effect=[TEST_CONTENT, b""])
            with pytest.raises(ValueError, match="Invalid path: directory traversal detected"):
                await store_file(in_file=mock_file, path=path_attempt, settings=settings)


@pytest.mark.asyncio
async def test_store_file_safe_paths_allowed() -> None:
    """Test that safe paths with dots are allowed."""
    with tempfile.TemporaryDirectory() as temp_dir:
        settings = BaseKwikSettings(UPLOADS_DIR=temp_dir)

        # These paths should be safe and allowed
        safe_paths = [
            "images/..valid",  # backslash literal in filename is safe on Unix
            "docs/file.name",  # normal path
            "images/icons",  # normal nested path
        ]

        for safe_path in safe_paths:
            mock_file = MagicMock(spec=UploadFile)
            mock_file.read = AsyncMock(side_effect=[TEST_CONTENT, b""])

            # Should not raise an exception
            relative_path, file_size = await store_file(in_file=mock_file, path=safe_path, settings=settings)
            assert file_size == TEST_CONTENT_SIZE
            assert relative_path.startswith(f"{safe_path}/")


@pytest.mark.asyncio
async def test_store_file_backward_compatibility() -> None:
    """Test that the function works without explicit settings parameter."""
    # This creates the default settings internally
    mock_file = MagicMock(spec=UploadFile)
    mock_file.read = AsyncMock(side_effect=[TEST_CONTENT, b""])
    mock_file.filename = "test.txt"

    # Should work without settings parameter (creates default ./uploads)
    relative_path, file_size = await store_file(in_file=mock_file)

    assert isinstance(relative_path, str)
    assert file_size == TEST_CONTENT_SIZE
    assert "/" not in relative_path  # No subpath, just filename

    # Clean up the created ./uploads directory
    uploads_dir = Path("./uploads")
    if uploads_dir.exists():
        shutil.rmtree(uploads_dir)


@pytest.mark.asyncio
async def test_store_file_chunk_size_performance() -> None:
    """Test that large files are handled with 64KB chunks."""
    # Create a larger test content to verify chunking behavior
    large_content = b"x" * (128 * 1024)  # 128KB content
    expected_size = len(large_content)

    with tempfile.TemporaryDirectory() as temp_dir:
        settings = BaseKwikSettings(UPLOADS_DIR=temp_dir)
        mock_file = MagicMock(spec=UploadFile)

        # Simulate chunked reading: 64KB + 64KB + empty
        chunk_size = 65536  # 64KB
        mock_file.read = AsyncMock(side_effect=[large_content[:chunk_size], large_content[chunk_size:], b""])
        mock_file.filename = "large_test.bin"

        # Act
        relative_path, file_size = await store_file(in_file=mock_file, settings=settings)

        # Assert
        assert file_size == expected_size
        full_path = Path(temp_dir) / relative_path
        assert full_path.exists()
        assert full_path.stat().st_size == expected_size
