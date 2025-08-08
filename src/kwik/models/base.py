"""Database base configuration and declarative base."""

from typing import Any

from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Modern SQLAlchemy 2.0 declarative base class for all database models."""

    # Allow unmapped annotations during migration transition
    __allow_unmapped__ = True

    # Configure naming convention for constraints
    metadata = MetaData(
        naming_convention={
            "ix": "ix_%(column_0_label)s",
            "uq": "uq_%(table_name)s_%(column_0_name)s",
            "ck": "ck_%(table_name)s_%(constraint_name)s",
            "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
            "pk": "pk_%(table_name)s",
        }
    )

    # Common attributes that will be properly typed later
    id: Any
    __name__: str
    __tablename__: str
