from datetime import datetime
from typing import Optional

from .orm import ORMMixin


class RecordInfoMixin(ORMMixin):
    creation_time: datetime
    last_modification_time: Optional[datetime] = None
    creator_user_id: int
    last_modifier_user_id: Optional[int] = None
