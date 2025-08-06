"""Database model mixins for common functionality."""

from __future__ import annotations

from sqlalchemy import BigInteger, DateTime, ForeignKey, func
from sqlalchemy.orm import declared_attr, mapped_column


class TimeStampsMixin:
    """Mixin providing automatic creation and modification timestamps."""

    # Allow unmapped annotations during migration transition
    __allow_unmapped__ = True

    creation_time = mapped_column(DateTime, nullable=False, server_default=func.now())
    last_modification_time = mapped_column(
        DateTime,
        server_onupdate=func.now(),
        onupdate=func.now(),
    )


class UserMixin:
    """Mixin providing user tracking fields for record creation and modification."""

    # Allow unmapped annotations during migration transition
    __allow_unmapped__ = True

    @declared_attr
    def creator_user_id(self) -> mapped_column[int]:
        """Get reference to the user who created this record."""
        return mapped_column(BigInteger, ForeignKey("users.id"), nullable=False)

    @declared_attr
    def last_modifier_user_id(self) -> mapped_column[int]:
        """Get reference to the user who last modified this record."""
        return mapped_column(BigInteger, ForeignKey("users.id"))


class RecordInfoMixin(TimeStampsMixin, UserMixin):
    """Combined mixin providing both timestamps and user tracking functionality."""

    # Allow unmapped annotations during migration transition
    __allow_unmapped__ = True
