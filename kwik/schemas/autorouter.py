from typing import Generic

from pydantic.generics import GenericModel

from kwik.typings import BaseSchemaType


class Paginated(GenericModel, Generic[BaseSchemaType]):
    total: int
    data: list[BaseSchemaType]
