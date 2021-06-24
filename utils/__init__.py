import aiofiles
from fastapi import UploadFile
from uuid import uuid1
from typing import Tuple


async def store_file(in_file: UploadFile) -> Tuple[str, int]:
    # ...
    root_upload_directory = '/uploads'
    file_name = str(uuid1())
    out_file_path = root_upload_directory + '/' + file_name
    file_size = 0
    async with aiofiles.open(out_file_path, 'wb') as out_file:
        content = await in_file.read(1024)
        file_size += len(content)
        while content:
            await out_file.write(content)
            content = await in_file.read(1024)
            file_size += len(content)

    return file_name, file_size
