"""Database model mixins for common functionality."""

from __future__ import annotations

from sqlalchemy import BigInteger, Column, DateTime, ForeignKey, func
from sqlalchemy.ext.declarative import declared_attr


class TimeStampsMixin:
    """Mixin providing automatic creation and modification timestamps."""

    creation_time = Column(DateTime, nullable=False, server_default=func.now())
    last_modification_time = Column(
        DateTime,
        server_onupdate=func.now(),
        onupdate=func.now(),
    )


class UserMixin:
    """Mixin providing user tracking fields for record creation and modification."""

    @declared_attr
    def creator_user_id(self) -> Column:
        """Get reference to the user who created this record."""
        return Column(BigInteger, ForeignKey("users.id"), nullable=False)

    @declared_attr
    def last_modifier_user_id(self) -> Column:
        """Get reference to the user who last modified this record."""
        return Column(BigInteger, ForeignKey("users.id"))


class RecordInfoMixin(TimeStampsMixin, UserMixin):
    """Combined mixin providing both timestamps and user tracking functionality."""
