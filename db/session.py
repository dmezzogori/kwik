from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from app.kwik.core.config import settings


def get_db() -> Generator:
    with DBContextManager() as db:
        yield db


class DBContextManager:
    def __init__(self, db_uri=settings.SQLALCHEMY_DATABASE_URI):
        engine = create_engine(db_uri, pool_pre_ping=True)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        self.db = SessionLocal()

    def __enter__(self) -> Session:
        return self.db

    def __exit__(self, exception_type, exception_value, exception_traceback):
        if exception_type is not None:
            self.db.rollback()
        else:
            self.db.commit()
        self.db.close()
