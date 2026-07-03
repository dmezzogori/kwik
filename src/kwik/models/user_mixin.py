"""Auth-essential user mixin for composing concrete user models."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, String
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import Mapped, declared_attr, mapped_column, relationship

if TYPE_CHECKING:
    from kwik.models.user import Permission, Role


class UserMixin:
    """
    Mixin providing the auth-essential columns and relationships for user models.

    Importing this module maps nothing: concrete user models are composed by the
    consuming application (or kwik's own ``DefaultUser``) as
    ``class MyUser(Base, UserMixin)`` with ``__tablename__ = "users"``.
    """

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String, index=True, nullable=False)
    surname: Mapped[str] = mapped_column(String, index=True, nullable=False)
    email: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    @declared_attr
    def roles(self) -> Mapped[list[Role]]:
        """Roles assigned to this user through the users_roles association table."""
        # Deferred import: models.user imports this module at module scope.
        from kwik.models.user import Role, UserRole  # noqa: PLC0415

        return relationship(
            Role,
            secondary="users_roles",
            primaryjoin=lambda: self.id == UserRole.user_id,
            secondaryjoin=lambda: UserRole.role_id == Role.id,
            viewonly=True,
        )

    @hybrid_property
    def permissions(self) -> list[Permission]:
        """Get all permissions for this user through their roles."""
        permissions = []
        for role in self.roles:
            permissions.extend(role.permissions)
        return permissions


__all__ = ["UserMixin"]
