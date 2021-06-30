from typing import Tuple
from uuid import uuid1

import aiofiles
from fastapi import UploadFile
from sqlalchemy.orm import Query

from app.kwik.typings import ModelType, ParsedSortingQuery, SortingQuery


async def store_file(*, in_file: UploadFile) -> Tuple[str, int]:
    # ...
    root_upload_directory = "/uploads"
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


def sort_query(*, model: ModelType, query: Query, sort: ParsedSortingQuery) -> Query:
    order_by = []
    for attr, order in sort:
        model_attr = getattr(model, attr)
        if order == "asc":
            order_by.append(model_attr.asc())
        else:
            order_by.append(model_attr.desc())
    return query.order_by(*order_by)
