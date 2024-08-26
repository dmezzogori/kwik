from datetime import datetime

from .orm import ORMMixin


class RecordInfoMixin(ORMMixin):
    creation_time: datetime
    last_modification_time: datetime | None = None
    creator_user_id: int
    last_modifier_user_id: int | None = None
