from sqlalchemy import Boolean, Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.kwik.db import Base, RecordInfoMixin


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    surname = Column(String, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean(), default=True)


class Role(Base, RecordInfoMixin):
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    is_active = Column(Boolean(), default=True)


class UserRole(Base, RecordInfoMixin):
    __tablename__ = "users_roles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    role_id = Column(Integer, ForeignKey("roles.id"))

    # user = relationship("User", foreign_keys=[user_id], viewonly=True)
    # role = relationship("Role", foreign_keys=[role_id])


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
