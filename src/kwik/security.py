"""Security utilities for JWT tokens and password hashing."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Final, Literal

import bcrypt
import jwt
from pydantic import ValidationError

from kwik import schemas
from kwik.core import BCRYPT_MAX_PASSWORD_BYTES

# Re-exported: applications configure and read the password policy through kwik.security.
from kwik.core.password_policy import configure_password_policy, password_min_length  # noqa: F401
from kwik.exceptions.base import TokenValidationError
from kwik.exceptions.users import PasswordTooLongError

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from kwik.auth import AuthSessionStore
    from kwik.crud.context import Context
    from kwik.models import User
    from kwik.settings import BaseKwikSettings

ALGORITHM: Final[str] = "HS256"
SECONDS_PER_MINUTE: Final[int] = 60


def create_token(
    *,
    user_id: int,
    impersonator_user_id: int | None = None,
    session_id: str | None = None,
    settings: BaseKwikSettings,
) -> schemas.Token:
    """
    Create OAuth2 bearer token response for user authentication.

    Without ``session_id`` the claim set is the one kwik 1.13 issued. With it the token also
    carries ``sid`` and ``typ`` and the response reports ``expires_in`` in seconds.
    """
    claims: dict[str, object] = {
        "exp": datetime.now(UTC) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        "sub": str(user_id),
        "kwik_impersonate": "" if impersonator_user_id is None else str(impersonator_user_id),
    }
    expires_in: int | None = None
    if session_id is not None:
        claims["sid"] = session_id
        claims["typ"] = "access"
        expires_in = settings.ACCESS_TOKEN_EXPIRE_MINUTES * SECONDS_PER_MINUTE

    access_token = jwt.encode(claims, settings.SECRET_KEY, algorithm=ALGORITHM)

    return schemas.Token(access_token=access_token, token_type="bearer", expires_in=expires_in)  # noqa: S106


def create_refresh_token(
    *,
    user_id: int,
    session_id: str,
    token_id: str,
    expires_at: datetime,
    settings: BaseKwikSettings,
) -> str:
    """
    Encode a refresh token for one generation of a session.

    The token has no ``iat`` (PyJWT rejects an ``iat`` in the future, which breaks callers
    driving an injected clock) and ``jti`` identifies the generation, so encoding the same
    arguments twice yields the same string.
    """
    return jwt.encode(
        {
            "typ": "refresh",
            "sub": str(user_id),
            "sid": session_id,
            "jti": token_id,
            "exp": expires_at,
        },
        settings.SECRET_KEY,
        algorithm=ALGORITHM,
    )


def decode_token(
    *,
    token: str,
    settings: BaseKwikSettings,
    token_type: Literal["access", "refresh"] = "access",  # noqa: S107
) -> schemas.TokenPayload:
    """Decode and validate a JWT, returning its payload; the token must be of ``token_type``."""
    try:
        claims = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        if claims.get("typ") == "refresh":
            # Refresh tokens carry no impersonation claim; the payload schema requires one.
            claims.setdefault("kwik_impersonate", "")
        payload = schemas.TokenPayload(**claims)
    except (jwt.PyJWTError, ValidationError):
        raise TokenValidationError from None
    if payload.typ != token_type:
        raise TokenValidationError
    return payload


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify plain password against bcrypt hashed password.

    Returns ``False`` rather than raising for malformed hashes and for passwords
    longer than :data:`~kwik.core.BCRYPT_MAX_PASSWORD_BYTES`, which bcrypt >=5.0.0
    rejects outright.
    """
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except (ValueError, TypeError):
        # Return False for invalid hash formats
        return False


def get_password_hash(password: str) -> str:
    """
    Generate bcrypt hash for password using direct bcrypt implementation.

    The request schemas reject over-long passwords before they reach this point;
    the check is repeated here so callers that bypass schema validation get a
    typed error instead of the bare ``ValueError`` bcrypt >=5.0.0 raises.

    Raises:
        PasswordTooLongError: If the UTF-8 encoding of ``password`` exceeds
            :data:`~kwik.core.BCRYPT_MAX_PASSWORD_BYTES`.

    """
    encoded = password.encode("utf-8")
    if len(encoded) > BCRYPT_MAX_PASSWORD_BYTES:
        raise PasswordTooLongError(len(encoded))
    return bcrypt.hashpw(encoded, bcrypt.gensalt()).decode("utf-8")


def generate_password_reset_token(*, email: str, settings: BaseKwikSettings, password_hash: str) -> str:
    """
    Generate a self-invalidating JWT password reset token.

    Embeds a fingerprint ("pwd") of the user's current hashed password so the
    token stops verifying once the password changes.
    """
    delta = timedelta(hours=48)  # Default 48 hours for password reset token
    now = datetime.now(tz=UTC)
    expires = now + delta
    exp = expires.timestamp()
    fingerprint = hashlib.sha256(password_hash.encode("utf-8")).hexdigest()[:16]
    return jwt.encode(
        {"exp": exp, "nbf": now, "sub": email, "pwd": fingerprint},
        settings.SECRET_KEY,
        algorithm=ALGORITHM,
    )


def verify_password_reset_token(token: str, settings: BaseKwikSettings, context: Context) -> str | None:
    """
    Verify a password reset token against the user's current password hash.

    Decodes the token, looks up the user by the ``sub`` email claim, and returns
    the email only when the user exists, is active, and the ``pwd`` fingerprint
    matches a freshly recomputed fingerprint of the current ``hashed_password``.
    Returns ``None`` on any JWT error, unknown/inactive user, or mismatch.
    """
    # Local imports to avoid circular dependency: crud.users imports security for hashing
    from kwik.crud import crud_users  # noqa: PLC0415

    try:
        decoded_token = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.PyJWTError:
        return None

    email = decoded_token.get("sub")
    fingerprint = decoded_token.get("pwd")
    if email is None or fingerprint is None:
        return None

    user = crud_users.get_by_email(email=email, context=context)
    if user is None or not user.is_active:
        return None

    current_fingerprint = hashlib.sha256(user.hashed_password.encode("utf-8")).hexdigest()[:16]
    if current_fingerprint != fingerprint:
        return None

    return email


def authenticate_from_token(
    *,
    token: str,
    settings: BaseKwikSettings,
    session: Session,
    store: AuthSessionStore | None = None,
) -> User:
    """
    Validate a JWT token and return the corresponding user.

    Convenience function for authenticating outside FastAPI's dependency injection
    (e.g., SSE endpoints, Celery tasks, CLI scripts).

    Args:
        token: Raw JWT string.
        settings: Application settings (provides SECRET_KEY and ALGORITHM).
        session: SQLAlchemy session for user lookup.
        store: The application's auth session store; when given, the token's session
            must be active.

    Returns:
        The authenticated User ORM object.

    Raises:
        TokenValidationError: If the token is invalid or expired.
        InvalidBearerTokenError: If ``store`` is given and the token's session is not active.
        AccessDeniedError: If the user does not exist.

    """
    # Local imports to avoid circular dependencies: crud.users and kwik.auth import security
    from kwik.auth import require_active_session  # noqa: PLC0415
    from kwik.crud import crud_users  # noqa: PLC0415
    from kwik.crud.context import Context  # noqa: PLC0415
    from kwik.exceptions import AccessDeniedError  # noqa: PLC0415

    payload = decode_token(token=token, settings=settings)
    require_active_session(payload=payload, store=store)
    if payload.sub is None:
        raise AccessDeniedError
    context = Context(session=session, user=None)
    user = crud_users.get(entity_id=int(payload.sub), context=context)
    if user is None:
        raise AccessDeniedError
    return user
