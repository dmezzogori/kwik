from sqlalchemy import Boolean, Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from kwik.db import Base, RecordInfoMixin


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    surname = Column(String, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean(), default=True)

    roles = relationship(
        "Role",
        secondary="users_roles",
        primaryjoin="User.id==UserRole.user_id",
        secondaryjoin="UserRole.role_id==Role.id",
        viewonly=True,
    )

    @property
    def permissions(self):
        return [permission for role in self.roles for permission in role.permissions]


class Role(Base, RecordInfoMixin):
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    is_active = Column(Boolean(), default=True, nullable=False)
    is_locked = Column(Boolean(), default=False, nullable=False)

    permissions = relationship(
        "Permission", secondary="roles_permissions", viewonly=True
    )


class UserRole(Base, RecordInfoMixin):
    __tablename__ = "users_roles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    role_id = Column(Integer, ForeignKey("roles.id"))


class Permission(Base, RecordInfoMixin):
    __tablename__ = "permissions"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)


class RolePermission(Base, RecordInfoMixin):
    __tablename__ = "roles_permissions"

    id = Column(Integer, primary_key=True, index=True)
    role_id = Column(Integer, ForeignKey("roles.id"))
    permission_id = Column(Integer, ForeignKey("permissions.id"))

    role = relationship("Role")
    permission = relationship("Permission")
