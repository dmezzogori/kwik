"""Database model mixins for common functionality."""

from __future__ import annotations

from datetime import datetime  # noqa: TC003

from sqlalchemy import BigInteger, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, declared_attr, mapped_column


class TimeStampsMixin:
    """Mixin providing automatic creation and modification timestamps."""

    creation_time: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    last_modification_time: Mapped[datetime | None] = mapped_column(
        DateTime,
        server_onupdate=func.now(),
        onupdate=func.now(),
    )


class UserMixin:
    """Mixin providing user tracking fields for record creation and modification."""

    @declared_attr
    def creator_user_id(self) -> Mapped[int]:
        """Get reference to the user who created this record."""
        return mapped_column(BigInteger, ForeignKey("users.id"))

    @declared_attr
    def last_modifier_user_id(self) -> Mapped[int | None]:
        """Get reference to the user who last modified this record."""
        return mapped_column(BigInteger, ForeignKey("users.id"))


class RecordInfoMixin(TimeStampsMixin, UserMixin):
    """Combined mixin providing both timestamps and user tracking functionality."""


__all__ = ["RecordInfoMixin", "TimeStampsMixin", "UserMixin"]
