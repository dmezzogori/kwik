from sqlalchemy import Boolean, Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship

from app.kwik.db import Base


class User(Base):
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    surname = Column(String, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean(), default=True)

class Role(Base):
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    is_active = Column(Boolean(), default=True)


class UserRole(Base):
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("user.id"))
    role_id = Column(Integer, ForeignKey("role.id"))


class Permission(Base):
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)


class RolePermission(Base):
    __tablename__ = 'role_permission'

    id = Column(Integer, primary_key=True, index=True)
    role_id = Column(Integer, ForeignKey("role.id"))
    permission_id = Column(Integer, ForeignKey("permission.id"))

    role = relationship('Role')
    permission = relationship('Permission')
