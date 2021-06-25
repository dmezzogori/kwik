import aiofiles
from fastapi import UploadFile
from uuid import uuid1
from typing import Tuple

from app.kwik.typings import SortingQuery, ParsedSortingQuery


async def store_file(*, in_file: UploadFile) -> Tuple[str, int]:
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


def parse_sorting_query(*, sorting: SortingQuery) -> ParsedSortingQuery:
    sort = []
    for elem in sorting.split(','):
        if ':' in elem:
            attr, order = elem.split(':')
        else:
            attr = elem
            order = 'asc'
        sort.append((attr, order))
    return sort


def sort_query(*, model, query, sort: ParsedSortingQuery):
    order_by = []
    for attr, order in sort:
        model_attr = getattr(model, attr)
        if order == 'asc':
            order_by.append(model_attr.asc())
        else:
            order_by.append(model_attr.desc())
    return query.order_by(*order_by)
