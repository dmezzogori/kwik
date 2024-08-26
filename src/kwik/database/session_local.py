from __future__ import annotations

from kwik.database.engine import engine
from sqlalchemy.orm import sessionmaker

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)
