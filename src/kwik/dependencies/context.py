from typing import Annotated

from sqlalchemy.orm import Session

from kwik.crud import Context, NoUserCtx, UserCtx

from .users import current_user


def _get_no_user_context(session: Session) -> NoUserCtx:
    """Get a context for a user that is not logged in."""
    return Context(session=session, user=None)


def _get_user_context(session: Session, user: current_user) -> UserCtx:
    """Get a context for a logged-in user."""
    return Context(session=session, user=user)


UserContext = Annotated[UserCtx, _get_user_context]
NoUserContext = Annotated[NoUserCtx, _get_no_user_context]


__all__ = ["NoUserContext", "UserContext"]
