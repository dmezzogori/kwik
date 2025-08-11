from collections.abc import Generator
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.orm import Session as _Session

import kwik.logger


def _get_session(request: Request) -> Generator[_Session, None, None]:
    session: _Session = request.app.state.SessionLocal()
    try:
        yield session
    except Exception as e:
        kwik.logger.exception(f"Error occurred while processing request: {e}")
        session.rollback()
        raise
    finally:
        session.close()


Session = Annotated[_Session, Depends(_get_session)]
