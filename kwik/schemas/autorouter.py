from typing import Generic

from kwik.typings import BaseSchemaType
from pydantic.generics import GenericModel


class Paginated(GenericModel, Generic[BaseSchemaType]):
    total: int
    data: list[BaseSchemaType]
