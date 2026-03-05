"""Security utilities for JWT tokens and password hashing."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Final

import bcrypt
import jwt
from pydantic import ValidationError

from kwik import schemas
from kwik.exceptions.base import TokenValidationError

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from kwik.models import User
    from kwik.settings import BaseKwikSettings

ALGORITHM: Final[str] = "HS256"


def create_token(
    *,
    user_id: int,
    impersonator_user_id: int | None = None,
    settings: BaseKwikSettings,
) -> schemas.Token:
    """Create OAuth2 bearer token response for user authentication."""
    access_token = jwt.encode(
        {
            "exp": datetime.now(UTC) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
            "sub": str(user_id),
            "kwik_impersonate": "" if impersonator_user_id is None else str(impersonator_user_id),
        },
        settings.SECRET_KEY,
        algorithm=ALGORITHM,
    )

    return schemas.Token(access_token=access_token, token_type="bearer")  # noqa: S106


def decode_token(*, token: str, settings: BaseKwikSettings) -> schemas.TokenPayload:
    """Decode and validate JWT token, returning payload data."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        return schemas.TokenPayload(**payload)
    except (jwt.PyJWTError, ValidationError):
        raise TokenValidationError from None


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify plain password against bcrypt hashed password."""
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except (ValueError, TypeError):
        # Return False for invalid hash formats
        return False


def get_password_hash(password: str) -> str:
    """Generate bcrypt hash for password using direct bcrypt implementation."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def generate_password_reset_token(email: str, settings: BaseKwikSettings) -> str:
    """Generate JWT token for password reset with expiration."""
    delta = timedelta(hours=48)  # Default 48 hours for password reset token
    now = datetime.now(tz=UTC)
    expires = now + delta
    exp = expires.timestamp()
    return jwt.encode(
        {"exp": exp, "nbf": now, "sub": email},
        settings.SECRET_KEY,
        algorithm=ALGORITHM,
    )


def verify_password_reset_token(token: str, settings: BaseKwikSettings) -> str | None:
    """Verify password reset token and return email if valid."""
    decoded_token = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
    return decoded_token.get("sub", None)


def authenticate_from_token(
    *,
    token: str,
    settings: BaseKwikSettings,
    session: Session,
) -> User:
    """
    Validate a JWT token and return the corresponding user.

    Convenience function for authenticating outside FastAPI's dependency injection
    (e.g., SSE endpoints, Celery tasks, CLI scripts).

    Args:
        token: Raw JWT string.
        settings: Application settings (provides SECRET_KEY and ALGORITHM).
        session: SQLAlchemy session for user lookup.

    Returns:
        The authenticated User ORM object.

    Raises:
        AccessDeniedError: If the token is invalid or the user does not exist.

    """
    # Local imports to avoid circular dependency: crud.users imports security for hashing
    from kwik.crud import crud_users  # noqa: PLC0415
    from kwik.crud.context import Context  # noqa: PLC0415
    from kwik.exceptions import AccessDeniedError  # noqa: PLC0415

    payload = decode_token(token=token, settings=settings)
    if payload.sub is None:
        raise AccessDeniedError
    context = Context(session=session, user=None)
    user = crud_users.get(entity_id=int(payload.sub), context=context)
    if user is None:
        raise AccessDeniedError
    return user
