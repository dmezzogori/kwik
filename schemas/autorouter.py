from typing import Generic, List

from pydantic.generics import GenericModel

from kwik.typings import BaseSchemaType


class Paginated(GenericModel, Generic[BaseSchemaType]):
    total: int
    data: List[BaseSchemaType]
