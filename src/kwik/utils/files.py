"""File handling and storage utilities."""

from pathlib import Path
from uuid import uuid1

import aiofiles
from fastapi import UploadFile

from kwik.settings import BaseKwikSettings


async def store_file(
    *, in_file: UploadFile, path: str | None = None, settings: BaseKwikSettings | None = None
) -> tuple[str, int]:
    """
    Store uploaded file to filesystem and return relative path and size.

    Stores an uploaded file to the filesystem with a UUID-based filename to prevent
    conflicts. Files are read and written in 64KB chunks to handle large files efficiently
    without loading them entirely into memory.

    Args:
        in_file: The uploaded file object from FastAPI
        path: Optional subdirectory path within uploads dir (e.g., "images" creates uploads/images)
        settings: Optional settings instance (creates default if not provided)

    Returns:
        tuple: (relative_file_path, file_size_in_bytes)

    Example:
        >>> rel_path, size = await store_file(in_file=upload, path="documents")
        >>> # File stored at {UPLOADS_DIR}/documents/{uuid}
        >>> # Returns: ("documents/{uuid}", file_size)

    Raises:
        ValueError: If path contains directory traversal attempts or is invalid

    """
    # Initialize settings if not provided (backward compatibility)
    if settings is None:
        settings = BaseKwikSettings()

    # Base uploads directory from settings
    base_uploads_dir = Path(settings.UPLOADS_DIR).resolve()

    # Ensure base uploads directory exists
    base_uploads_dir.mkdir(parents=True, exist_ok=True)

    # Handle optional subdirectory path with security validation
    target_dir = base_uploads_dir
    relative_subpath = ""

    if path is not None:
        # Clean the path and ensure it's relative
        clean_path = path.strip("/").strip("\\")
        if not clean_path:
            msg = "Invalid path: empty after cleaning"
            raise ValueError(msg)

        # Construct the target path using pathlib
        potential_path = base_uploads_dir / clean_path

        try:
            # Resolve the path and check it's within the base directory
            resolved_path = potential_path.resolve()
            resolved_path.relative_to(base_uploads_dir.resolve())
            target_dir = resolved_path
            relative_subpath = clean_path
        except ValueError as e:
            msg = "Invalid path: directory traversal detected"
            raise ValueError(msg) from e

        # Create subdirectory structure if it doesn't exist
        target_dir.mkdir(parents=True, exist_ok=True)

    # Generate unique filename using UUID to prevent conflicts
    file_name = str(uuid1())
    out_file_path = target_dir / file_name

    # Build relative path for return value
    relative_file_path = f"{relative_subpath}/{file_name}" if relative_subpath else file_name

    # Track file size during streaming
    file_size = 0

    # Stream file content in 64KB chunks to handle large files efficiently
    chunk_size = 65536  # 64KB
    async with aiofiles.open(out_file_path, "wb") as out_file:
        # Read first chunk
        content = await in_file.read(chunk_size)
        file_size += len(content)

        # Continue reading and writing chunks until file is complete
        while content:
            await out_file.write(content)
            content = await in_file.read(chunk_size)
            file_size += len(content)

    return relative_file_path, file_size
