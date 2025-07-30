"""Database engine configuration for SQLAlchemy."""

from __future__ import annotations

from sqlalchemy import create_engine

import kwik

engine = create_engine(
    url=kwik.settings.SQLALCHEMY_DATABASE_URI,
    pool_pre_ping=True,
    pool_size=kwik.settings.POSTGRES_MAX_CONNECTIONS // kwik.settings.BACKEND_WORKERS,
    max_overflow=0,
)

alternate_engine = None
if kwik.settings.alternate_db.ALTERNATE_SQLALCHEMY_DATABASE_URI is not None:
    alternate_engine = create_engine(url=kwik.settings.alternate_db.ALTERNATE_SQLALCHEMY_DATABASE_URI)
