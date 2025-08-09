from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from kwik.models import User


@dataclass(slots=True, frozen=True)
class Context[U: (None, User, User | None)]:
    session: Session
    user: U


type UserCtx = Context[User]
type MaybeUserCtx = Context[User | None]
type NoUserCtx = Context[None]
