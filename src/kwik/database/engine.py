"""Database engine configuration for SQLAlchemy."""

from __future__ import annotations

from sqlalchemy import create_engine

from kwik.core.settings import get_settings

settings = get_settings()
engine = create_engine(
    url=settings.SQLALCHEMY_DATABASE_URI,
    pool_pre_ping=True,
    pool_size=settings.POSTGRES_MAX_CONNECTIONS // settings.BACKEND_WORKERS,
    max_overflow=0,
)

alternate_engine = None
if settings.alternate_db.ALTERNATE_SQLALCHEMY_DATABASE_URI is not None:
    alternate_engine = create_engine(url=settings.alternate_db.ALTERNATE_SQLALCHEMY_DATABASE_URI)
