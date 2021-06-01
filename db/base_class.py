from typing import Any

from sqlalchemy.ext.declarative import as_declarative, declared_attr
from sqlalchemy import Column, BigInteger, DateTime, func, ForeignKey


@as_declarative()
class Base:
    id: Any
    __name__: str
    # Generate __tablename__ automatically
    @declared_attr
    def __tablename__(cls) -> str:
        return cls.__name__.lower()


class TimeStampsMixin:
    creation_time = Column(DateTime, nullable=False, default=func.now())
    last_modification_time = Column(DateTime, onupdate=func.now())


class UserMixin:

    @declared_attr
    def creator_user_id(self):
        return Column(BigInteger, ForeignKey("user.id"))

    @declared_attr
    def last_modifier_user_id(self):
        return Column(BigInteger, ForeignKey("user.id"))
