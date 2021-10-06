from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class RecordInfoMixin(BaseModel):
    creation_time: datetime
    last_modification_time: Optional[datetime] = None
    creator_user_id: int
    last_modifier_user_id: Optional[int] = None

    class Config:
        orm_mode = True
