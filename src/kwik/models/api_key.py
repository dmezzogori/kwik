"""
API key model for external service authentication.

Provides a hashed-key-based authentication mechanism as an alternative
to JWT bearer tokens, allowing external systems to call API endpoints
without a login session.
"""

from __future__ import annotations

from datetime import datetime  # noqa: TC003
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from .user import User


class ApiKey(Base):
    """
    Persistent API key record.

    Keys are stored as SHA-256 hashes. The plaintext key is returned
    exactly once at creation time and never persisted. The ``key_suffix``
    (last 4 characters) is stored in cleartext for display/identification
    in management UIs.

    Attributes:
        id: Auto-increment primary key.
        user_id: FK to the owning user whose permissions the key inherits.
        name: Human-readable label (e.g. "ERP Integration").
        prefix: Key prefix for recognition (always ``tbk_``).
        key_hash: SHA-256 hex digest of the full plaintext key.
        key_suffix: Last 4 characters of the plaintext key.
        expires_at: Optional expiry timestamp; null means never expires.
        revoked_at: Timestamp when revoked; null means active.
        last_used_at: Updated on each successful authentication.
        created_at: Auto-set on row creation.
        user: Relationship to the owning ``User``.

    """

    __tablename__ = "api_keys"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    prefix: Mapped[str] = mapped_column(String(8), nullable=False, default="tbk_")
    key_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    key_suffix: Mapped[str] = mapped_column(String(4), nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())

    user: Mapped[User] = relationship("User", lazy="joined")


__all__ = ["ApiKey"]
