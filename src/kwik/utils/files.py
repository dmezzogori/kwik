"""File handling and storage utilities."""

from pathlib import Path
from uuid import uuid1

import aiofiles
from fastapi import UploadFile


async def store_file(*, in_file: UploadFile, path: str | None = None) -> tuple[str, int]:
    """
    Store uploaded file to filesystem and return filename and size.

    Stores an uploaded file to the filesystem with a UUID-based filename to prevent
    conflicts. Files are read and written in 1KB chunks to handle large files efficiently
    without loading them entirely into memory.

    Args:
        in_file: The uploaded file object from FastAPI
        path: Optional subdirectory path within /uploads (e.g., "images" creates /uploads/images)

    Returns:
        tuple: (generated_filename, file_size_in_bytes)

    Example:
        >>> filename, size = await store_file(in_file=upload, path="documents")
        >>> # File stored at /uploads/documents/{uuid}

    """
    # Base directory for all uploaded files
    root_upload_directory = "/uploads"

    # Handle optional subdirectory path with security validation
    if path is not None:
        # Validate path to prevent directory traversal attacks
        base_path = Path("/uploads").resolve()

        # Clean the path and ensure it's relative
        clean_path = path.strip("/").strip("\\")
        if not clean_path:
            msg = "Invalid path: empty after cleaning"
            raise ValueError(msg)

        # Construct and resolve the full path
        full_path = (base_path / clean_path).resolve()

        # Security check: ensure the resolved path is within the uploads directory
        if not str(full_path).startswith(str(base_path) + "/"):
            msg = "Invalid path: directory traversal detected"
            raise ValueError(msg)

        root_upload_directory = str(full_path)

        # Create directory structure if it doesn't exist
        Path(root_upload_directory).mkdir(parents=True, exist_ok=True)

    # Generate unique filename using UUID to prevent conflicts
    file_name = str(uuid1())
    out_file_path = root_upload_directory + "/" + file_name

    # Track file size during streaming
    file_size = 0

    # Stream file content in 1KB chunks to handle large files efficiently
    async with aiofiles.open(out_file_path, "wb") as out_file:
        # Read first chunk
        content = await in_file.read(1024)
        file_size += len(content)

        # Continue reading and writing chunks until file is complete
        while content:
            await out_file.write(content)
            content = await in_file.read(1024)
            file_size += len(content)

    return file_name, file_size
