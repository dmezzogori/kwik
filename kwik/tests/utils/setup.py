import os
from typing import Callable

from fastapi import FastAPI
from kwik.database.base import Base
from kwik.database.session import DBContextManager
from kwik.database.session import get_db_from_request
import pytest


def setup_test_db(*, path: str, init_func: Callable, app: FastAPI, **kwargs):
    """
    Initialize a SQLite test database.
    """

    def init_test_db():
        # Create a temporary database
        if os.path.exists(path):
            os.remove(path)
        os.mknod(path)

        # Initialize the database
        # Documentation for check_same_thread=False
        # https://fastapi.tiangolo.com/tutorial/sql-databases/#note
        with DBContextManager(db_uri=f"sqlite:///{path}", connect_args={"check_same_thread": False}) as db_cxt:
            Base.metadata.create_all(bind=db_cxt.get_bind())
            init_func(db_cxt, **kwargs)

        # Pause the fixture
        yield

        # Cleanup
        os.remove(path)

    pytest.fixture(scope="session", autouse=True)(init_test_db)

    def db():
        with DBContextManager(db_uri=f"sqlite:///{path}", connect_args={"check_same_thread": False}) as db_cxt:
            yield db_cxt

    app.dependency_overrides[get_db_from_request] = db
    db = pytest.fixture(scope="session")(db)
    return db
