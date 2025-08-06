"""Database models for user management and permissions."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from kwik.models.user import Permission

from kwik.database.base import Base
from kwik.database.mixins import RecordInfoMixin


class User(Base):
    """Database model for user accounts with authentication and authorization."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String, index=True)
    surname: Mapped[str] = mapped_column(String, index=True)
    email: Mapped[str] = mapped_column(String, unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False)

    roles = relationship(
        "Role",
        secondary="users_roles",
        primaryjoin="User.id==UserRole.user_id",
        secondaryjoin="UserRole.role_id==Role.id",
        viewonly=True,
    )

    @property
    def permissions(self) -> list[Permission]:
        """Get all permissions from all user roles."""
        return [permission for role in self.roles for permission in role.permissions]


class Role(Base, RecordInfoMixin):
    """Database model for user roles with record tracking."""

    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str | None] = mapped_column(String, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_locked: Mapped[bool] = mapped_column(Boolean, default=False)

    permissions = relationship(
        "Permission",
        secondary="roles_permissions",
        viewonly=True,
    )


class UserRole(Base, RecordInfoMixin):
    """Database model for user-role associations with record tracking."""

    __tablename__ = "users_roles"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    role_id: Mapped[int | None] = mapped_column(ForeignKey("roles.id"))


class Permission(Base, RecordInfoMixin):
    """Database model for system permissions with record tracking."""

    __tablename__ = "permissions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String, index=True)


class RolePermission(Base, RecordInfoMixin):
    """Database model for role-permission associations with record tracking."""

    __tablename__ = "roles_permissions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    role_id: Mapped[int | None] = mapped_column(ForeignKey("roles.id"))
    permission_id: Mapped[int | None] = mapped_column(ForeignKey("permissions.id"))

    role = relationship("Role")
    permission = relationship("Permission")
