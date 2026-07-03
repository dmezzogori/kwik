"""
Default concrete user model for applications that do not register a custom one.

This module is imported ONLY by ``kwik.kernel.get_kernel()``'s fallback path —
never eagerly from kwik source: importing it maps the ``users`` table, which
must not happen when a consuming application composes its own user model.
"""

from kwik.models.base import Base
from kwik.models.user_mixin import UserMixin


class DefaultUser(Base, UserMixin):
    """Default user model for zero-configuration kwik applications."""

    __tablename__ = "users"


__all__ = ["DefaultUser"]
