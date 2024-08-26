from __future__ import annotations

from typing import Callable

from kwik.database import DBContextManager
from kwik.database.base import Base


def init_test_db(init_db: Callable, *args, **kwargs) -> None:
    # Initialize the database
    with DBContextManager() as db:
        Base.metadata.create_all(bind=db.get_bind())
        init_db(*args, **kwargs)


def drop_test_db() -> None:
    # Drop the database
    with DBContextManager() as db:
        Base.metadata.drop_all(bind=db.get_bind())
