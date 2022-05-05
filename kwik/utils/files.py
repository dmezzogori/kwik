from pathlib import Path
from typing import Tuple
from uuid import uuid1

import aiofiles
from fastapi import UploadFile


async def store_file(*, in_file: UploadFile, path: str | None = None) -> Tuple[str, int]:
    root_upload_directory = "/uploads"

    if path is not None and len(path) > 1:
        if path[0] != "/":
            path = "/" + path
        # TODO: verificare i permessi
        root_upload_directory += path
        if root_upload_directory[-1] == "/":
            root_upload_directory = root_upload_directory[:-1]
        Path(root_upload_directory).mkdir(parents=True, exist_ok=True)

    file_name = str(uuid1())
    out_file_path = root_upload_directory + "/" + file_name
    file_size = 0
    async with aiofiles.open(out_file_path, "wb") as out_file:
        content = await in_file.read(1024)
        file_size += len(content)
        while content:
            await out_file.write(content)
            content = await in_file.read(1024)
            file_size += len(content)

    return file_name, file_size
