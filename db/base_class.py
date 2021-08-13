from typing import Any

from sqlalchemy.ext.declarative import as_declarative, declared_attr
from sqlalchemy import Column, BigInteger, DateTime, func, ForeignKey


@as_declarative()
class Base:

    id: Any
    __name__: str
    __tablename__: str


class TimeStampsMixin:
    creation_time = Column(DateTime, nullable=False, default=func.now())  # TODO: mettere default via sql
    last_modification_time = Column(DateTime, onupdate=func.now())


class UserMixin:
    @declared_attr
    def creator_user_id(self):
        return Column(BigInteger, ForeignKey("users.id"), nullable=False)  # TODO: fix, nullable=True

    @declared_attr
    def last_modifier_user_id(self):
        return Column(BigInteger, ForeignKey("users.id"))


class RecordInfoMixin(TimeStampsMixin, UserMixin):
    pass
