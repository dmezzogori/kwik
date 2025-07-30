from __future__ import annotations

from sqlalchemy import BigInteger, Boolean, Column, DateTime, ForeignKey, func
from sqlalchemy.ext.declarative import declared_attr


class TimeStampsMixin:
    creation_time = Column(DateTime, nullable=False, server_default=func.now())
    last_modification_time = Column(
        DateTime, server_onupdate=func.now(), onupdate=func.now(),
    )


class UserMixin:
    @declared_attr
    def creator_user_id(self):
        """Reference to the user who created this record."""
        return Column(BigInteger, ForeignKey("users.id"), nullable=False)

    @declared_attr
    def last_modifier_user_id(self):
        """Reference to the user who last modified this record."""
        return Column(BigInteger, ForeignKey("users.id"))


class RecordInfoMixin(TimeStampsMixin, UserMixin):
    pass


class SoftDeleteMixin(RecordInfoMixin):
    @declared_attr
    def deleted(self):
        """Boolean flag indicating if record is soft-deleted."""
        return Column(Boolean, default=False)


class LogMixin:
    pass
