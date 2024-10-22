from __future__ import annotations

from kwik.database.engine import engine, alternate_engine
from sqlalchemy.orm import sessionmaker

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
