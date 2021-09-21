import inspect

from fastapi import Request
from sqlalchemy import create_engine
from sqlalchemy import event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.sql import visitors

from app.kwik.core.config import settings
from app.kwik.db.base_class import SoftDeleteMixin
from app.kwik.logging import logger


def get_db_from_request(request: Request):
    return request.state.db


class DBContextManager:
    def __init__(self, db_uri=settings.SQLALCHEMY_DATABASE_URI):
        engine = create_engine(db_uri, pool_pre_ping=True)
        db = sessionmaker(autocommit=False, autoflush=False, bind=engine)()
        self.db = db

        # https://stackoverflow.com/questions/44522391/implementing-a-soft-delete-system-using-sqlalchemy
        # https://github.com/sqlalchemy/sqlalchemy/wiki/FilteredQuery
        # @event.listens_for(db, "do_orm_execute")
        # def _do_orm_execute(orm_execute_state):
        #     tables = set()
        #     for visitor in visitors.iterate(orm_execute_state.statement):
        #         if (
        #             visitor.__visit_name__ == "table"
        #             and inspect.isclass(visitor.entity_namespace)
        #             and issubclass(visitor.entity_namespace, SoftDeleteMixin)
        #         ):
        #             tables.add(visitor.entity_namespace)
        #
        #     tables = list(tables)
        #     if tables:
        #         orm_execute_state.statement = orm_execute_state.statement.filter(
        #             *(table.deleted == False for table in tables)
        #         )
        #     logger.error(orm_execute_state.statement)

    def __enter__(self) -> Session:
        return self.db

    def __exit__(self, exception_type, exception_value, exception_traceback):
        if exception_type is not None:
            self.db.rollback()
        else:
            self.db.commit()

        self.db.close()
