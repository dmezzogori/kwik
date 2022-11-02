from contextlib import contextmanager
from typing import Generator

import kwik
from kwik.database.db_context_manager import DBContextManager
from kwik.database.db_context_var import db_conn_ctx_var


@contextmanager
def test_db(*, db_path: str, setup=True) -> Generator:
    # Documentation for check_same_thread=False
    # https://fastapi.tiangolo.com/tutorial/sql-databases/#note
    with DBContextManager(
        db_uri=f"sqlite:///{db_path}", connect_args={"check_same_thread": False}, settings=kwik.settings
    ) as db_cxt:
        if setup:
            superuser = kwik.crud.user.get_by_email(email=kwik.settings.FIRST_SUPERUSER)
            from kwik.database.db_context_var import current_user_ctx_var
            current_user_ctx_var.set(superuser)

            db_conn_ctx_var.set(db_cxt)

        yield db_cxt
