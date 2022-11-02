import os
from typing import Callable

import kwik
from kwik.database.base import Base


def init_test_db(db_path: str, init_db: Callable, *args, **kwargs) -> None:
    # Create a temporary database
    if os.path.exists(db_path):
        os.remove(db_path)
    os.mknod(db_path)

    # Initialize the database
    with kwik.utils.tests.test_db(db_path=db_path, setup=False) as db:
        Base.metadata.create_all(bind=db.get_bind())
        init_db(*args, **kwargs)
