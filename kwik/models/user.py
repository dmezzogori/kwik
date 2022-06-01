from kwik.database.base import Base
from kwik.database.mixins import RecordInfoMixin, SoftDeleteMixin
from sqlalchemy import Boolean, Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    surname = Column(String, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean(), default=True)
    is_superuser = Column(Boolean(), default=False)

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


class Role(Base, SoftDeleteMixin):
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    is_active = Column(Boolean(), default=True, nullable=False)
    is_locked = Column(Boolean(), default=False, nullable=False)

    permissions = relationship("Permission", secondary="roles_permissions", viewonly=True)


class UserRole(Base, SoftDeleteMixin):
    __tablename__ = "users_roles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    role_id = Column(Integer, ForeignKey("roles.id"))


class Permission(Base, RecordInfoMixin):
    __tablename__ = "permissions"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)


class RolePermission(Base, RecordInfoMixin):
    __tablename__ = "roles_permissions"

    id = Column(Integer, primary_key=True, index=True)
    role_id = Column(Integer, ForeignKey("roles.id"))
    permission_id = Column(Integer, ForeignKey("permissions.id"))

    role = relationship("Role")
    permission = relationship("Permission")
