"""Database models for user management and permissions."""

from __future__ import annotations

from sqlalchemy import Boolean, ForeignKey, String, func, select
from sqlalchemy.orm import Mapped, column_property, mapped_column, relationship

from .base import Base
from .mixins import RecordInfoMixin
from .user_mixin import UserMixin  # noqa: TC001 — runtime import: _user_model()'s return type


def _user_model() -> type[UserMixin]:
    """Resolve the registered user model; deferred until mapper configuration."""
    from kwik.kernel import get_kernel  # noqa: PLC0415 — deferred to avoid circular import

    return get_kernel().user_model


class Role(Base, RecordInfoMixin):
    """Database model for user roles with record tracking."""

    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String, index=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    users = relationship(
        _user_model,
        secondary="users_roles",
        primaryjoin=lambda: Role.id == UserRole.role_id,
        secondaryjoin=lambda: UserRole.user_id == _user_model().id,
        viewonly=True,
    )

    permissions: Mapped[list[Permission]] = relationship(
        "Permission",
        secondary="roles_permissions",
        viewonly=True,
    )


class UserRole(Base, RecordInfoMixin):
    """Database model for user-role associations with record tracking."""

    __tablename__ = "users_roles"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    role_id: Mapped[int] = mapped_column(ForeignKey("roles.id"), nullable=False)


# Deferred column_property: must be defined after UserRole to avoid forward reference.
Role.user_count = column_property(
    select(func.count(UserRole.id)).where(UserRole.role_id == Role.id).correlate_except(UserRole).scalar_subquery()
)


class Permission(Base, RecordInfoMixin):
    """Database model for system permissions with record tracking."""

    __tablename__ = "permissions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String, index=True, nullable=False)

    roles: Mapped[list[Role]] = relationship(
        "Role",
        secondary="roles_permissions",
        viewonly=True,
    )


class RolePermission(Base, RecordInfoMixin):
    """Database model for role-permission associations with record tracking."""

    __tablename__ = "roles_permissions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    role_id: Mapped[int] = mapped_column(ForeignKey("roles.id"), nullable=False)
    permission_id: Mapped[int] = mapped_column(ForeignKey("permissions.id"), nullable=False)


__all__ = ["Permission", "Role", "RolePermission", "UserRole"]
