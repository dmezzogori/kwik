"""Database models for user management and permissions."""

from __future__ import annotations

from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base
from .mixins import RecordInfoMixin


class User(Base):
    """Database model for user accounts with authentication and authorization."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String, index=True, nullable=False)
    surname: Mapped[str] = mapped_column(String, index=True, nullable=False)
    email: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    roles: Mapped[list[Role]] = relationship(
        "Role",
        secondary="users_roles",
        primaryjoin="User.id==UserRole.user_id",
        secondaryjoin="UserRole.role_id==Role.id",
        viewonly=True,
    )

    @hybrid_property
    def permissions(self) -> list[Permission]:
        """Get all permissions for this user through their roles."""
        permissions = []
        for role in self.roles:
            permissions.extend(role.permissions)
        return permissions


class Role(Base, RecordInfoMixin):
    """Database model for user roles with record tracking."""

    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String, index=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    users: Mapped[list[User]] = relationship(
        "User",
        secondary="users_roles",
        primaryjoin="Role.id==UserRole.role_id",
        secondaryjoin="UserRole.user_id==User.id",
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


__all__ = ["Permission", "Role", "RolePermission", "User", "UserRole"]
