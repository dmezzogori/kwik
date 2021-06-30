from typing import Any, Dict, List, Optional, Tuple, TypeVar

from pydantic import BaseModel

from app.kwik.db.base_class import Base
from app.kwik.schemas.synth import MyBaseModel

ModelType = TypeVar("ModelType", bound=Base)

BaseSchemaType = TypeVar("BaseSchemaType", bound=MyBaseModel)
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)


SortingQuery = str
ParsedSortingQuery = Optional[List[Tuple[str, str]]]
FilterQuery = Dict[str, Any]
PaginatedQuery = Dict[str, int]
