"""Local database session factory configuration."""

from __future__ import annotations

from sqlalchemy.orm import sessionmaker

from kwik.database.engine import alternate_engine, engine

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


AlternateSessionLocal = None
if alternate_engine is not None:
    AlternateSessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=alternate_engine,
    )
