"""Database base configuration and declarative base."""

from sqlalchemy.ext.declarative import as_declarative


@as_declarative()
class Base:
    """SQLAlchemy declarative base class for all database models."""

    id: int
    __name__: str
    __tablename__: str
